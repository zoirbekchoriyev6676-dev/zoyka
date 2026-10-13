"""Persistent monitoring, idempotent events and recoverable exam drafts.
Images never leave the student's browser. No API key is needed.
"""
import json
import time
from contextlib import contextmanager
from database.db import get_db_connection

LIMIT = 5
SCHEMA = """
CREATE TABLE IF NOT EXISTS camera_exam_progress (
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 test_id INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
 answers TEXT NOT NULL DEFAULT '{}', remaining REAL NOT NULL,
 running_since REAL, epoch INTEGER NOT NULL DEFAULT 0,
 look_count INTEGER NOT NULL DEFAULT 0, camera_status TEXT NOT NULL DEFAULT 'waiting',
 updated_at REAL NOT NULL, PRIMARY KEY(student_id,test_id)
);
CREATE TABLE IF NOT EXISTS camera_event_receipts (
 student_id INTEGER NOT NULL, test_id INTEGER NOT NULL, event_id TEXT NOT NULL,
 PRIMARY KEY(student_id,test_id,event_id)
);
CREATE INDEX IF NOT EXISTS idx_monitor_event_counts ON proctoring_events(test_id,student_id,event_type);
"""

def migrate(conn):
    conn.executescript(SCHEMA)
    conn.commit()

@contextmanager
def transaction():
    conn = get_db_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def access(conn, sid, tid):
    row = conn.execute('''SELECT t.duration_minutes,t.enable_camera,t.status,
        ta.group_id AS owner_group,s.group_id,
        a.status AS access_status
        FROM tests t JOIN teacher_assignments ta ON ta.id=t.assignment_id
        JOIN students s ON s.id=?
        LEFT JOIN test_groups_access a ON a.test_id=t.id AND a.group_id=s.group_id
        WHERE t.id=?''', (sid, tid)).fetchone()
    if not row or (row['group_id'] != row['owner_group'] and row['access_status'] is None):
        raise ValueError('Bu testga kirish ruxsati yo‘q.')
    if (row['access_status'] and row['access_status'] != 'active') or (not row['access_status'] and str(row['status']).lower() not in ('active','started')):
        raise ValueError('Test guruhingiz uchun faol emas.')
    return row

def settings(conn, tid, test):
    row = conn.execute('SELECT * FROM proctoring_settings WHERE test_id=?',(tid,)).fetchone()
    result = dict(row) if row else {'enable_camera': test['enable_camera'], 'camera_policy':'block', 'track_exit':1}
    result.update(look_away_limit=LIMIT, away_ms=2000, return_ms=1000)
    return result

def ensure(conn, sid, tid, test):
    conn.execute('''INSERT OR IGNORE INTO camera_exam_progress
        (student_id,test_id,remaining,updated_at) VALUES (?,?,?,?)''',
        (sid, tid, max(0, test['duration_minutes'] or 30)*60, time.time()))
    conn.execute("INSERT OR IGNORE INTO student_test_state(student_id,test_id,status) VALUES (?,?,'ACTIVE')", (sid, tid))

def freeze(conn,sid,tid):
    row=conn.execute('SELECT * FROM camera_exam_progress WHERE student_id=? AND test_id=?',(sid,tid)).fetchone()
    if row and row['running_since'] is not None:
        remaining=max(0,row['remaining']-max(0,time.time()-row['running_since']))
        conn.execute('UPDATE camera_exam_progress SET remaining=?,running_since=NULL WHERE student_id=? AND test_id=?',(remaining,sid,tid))

def snapshot(conn,sid,tid):
    p=conn.execute('SELECT * FROM camera_exam_progress WHERE student_id=? AND test_id=?',(sid,tid)).fetchone()
    st=conn.execute('SELECT status,block_reason FROM student_test_state WHERE student_id=? AND test_id=?',(sid,tid)).fetchone()
    if st['status'] != 'ACTIVE':
        freeze(conn,sid,tid)
        p=conn.execute('SELECT * FROM camera_exam_progress WHERE student_id=? AND test_id=?',(sid,tid)).fetchone()
    remaining=max(0,p['remaining']-(max(0,time.time()-p['running_since']) if p['running_since'] is not None else 0))
    return {'status':st['status'],'block_reason':st['block_reason'],'is_blocked':st['status']=='BLOCKED',
        'answers':json.loads(p['answers']),'remaining_seconds':remaining,'running':p['running_since'] is not None,
        'look_count':p['look_count'],'limit':LIMIT,'epoch':p['epoch'],'camera_status':p['camera_status']}

def save_answers(conn,sid,tid,answers):
    if answers is None: return
    if len(answers)>2000: raise ValueError('Javoblar soni juda ko‘p.')
    allowed={str(r['question_id']):set() for r in conn.execute('SELECT question_id FROM test_questions WHERE test_id=?',(tid,))}
    for r in conn.execute('SELECT id,question_id FROM question_options WHERE question_id IN (SELECT question_id FROM test_questions WHERE test_id=?)',(tid,)):
        allowed[str(r['question_id'])].add(r['id'])
    clean={}
    for key,value in answers.items():
        if str(key) not in allowed or isinstance(value,bool) or not isinstance(value,int) or value not in allowed[str(key)]:
            raise ValueError('Javob varianti testga mos emas.')
        clean[str(key)]=value
    conn.execute('UPDATE camera_exam_progress SET answers=?,updated_at=? WHERE student_id=? AND test_id=?',
                 (json.dumps(clean),time.time(),sid,tid))

def sync(sid,tid,answers=None,ready=None,camera_status=None):
    with transaction() as conn:
        test=access(conn,sid,tid); ensure(conn,sid,tid,test)
        state=snapshot(conn,sid,tid)
        if state['status']=='ACTIVE':
            if state['remaining_seconds']>0: save_answers(conn,sid,tid,answers)
            if ready is False: freeze(conn,sid,tid)
            elif ready is True:
                conn.execute('UPDATE camera_exam_progress SET running_since=COALESCE(running_since,?) WHERE student_id=? AND test_id=?',(time.time(),sid,tid))
        if camera_status is not None:
            conn.execute('UPDATE camera_exam_progress SET camera_status=?,updated_at=? WHERE student_id=? AND test_id=?',(camera_status[:80],time.time(),sid,tid))
        result=snapshot(conn,sid,tid);result['settings']=settings(conn,tid,test)
        return result

def report(sid,tid,event_type,event_id,epoch,answers=None,details=''):
    if event_type not in ('look_away','camera_error','camera_ready','face_missing','multiple_faces_notice','tab_switch','fullscreen_exit','reload'):
        raise ValueError('Noma’lum kuzatuv hodisasi.')
    with transaction() as conn:
        test=access(conn,sid,tid);ensure(conn,sid,tid,test)
        state=snapshot(conn,sid,tid)
        if conn.execute('SELECT 1 FROM camera_event_receipts WHERE student_id=? AND test_id=? AND event_id=?',(sid,tid,event_id)).fetchone():
            return state
        if state['status']!='ACTIVE' or epoch != state['epoch']: return state
        conf=settings(conn,tid,test)
        if event_type=='look_away' and not conf.get('enable_camera'): return state
        if state['remaining_seconds']>0: save_answers(conn,sid,tid,answers)
        conn.execute('INSERT INTO camera_event_receipts VALUES (?,?,?)',(sid,tid,event_id))
        counter=state['look_count']; limit=0
        if event_type=='look_away':
            counter+=1;limit=LIMIT
            conn.execute('UPDATE camera_exam_progress SET look_count=? WHERE student_id=? AND test_id=?',(counter,sid,tid))
        elif event_type in ('tab_switch','fullscreen_exit','reload'):
            key={'tab_switch':'tab_switch_limit','fullscreen_exit':'fullscreen_limit','reload':'reload_limit'}[event_type]
            limit=int(conf.get(key,3)) if conf.get('track_exit',1) else 0
            # Resume starts a fresh warning window while preserving history.
            last_resume=conn.execute("SELECT COALESCE(MAX(id),0) FROM proctoring_events WHERE student_id=? AND test_id=? AND event_type='admin_resume'",(sid,tid)).fetchone()[0]
            counter=conn.execute('SELECT COUNT(*) FROM proctoring_events WHERE student_id=? AND test_id=? AND event_type=? AND id>?',(sid,tid,event_type,last_resume)).fetchone()[0]+1
        if event_type=='camera_error':
            conn.execute("UPDATE camera_exam_progress SET camera_status='technical_error' WHERE student_id=? AND test_id=?",(sid,tid))
            if conf.get('camera_policy') in ('block','block_without_camera'): freeze(conn,sid,tid)
        if event_type=='camera_ready':
            conn.execute("UPDATE camera_exam_progress SET camera_status='ready' WHERE student_id=? AND test_id=?",(sid,tid))
        conn.execute('''INSERT INTO proctoring_events(student_id,test_id,event_type,details,counter)
                       VALUES (?,?,?,?,?)''',(sid,tid,event_type,details[:500],counter))
        message=''
        if limit>0 and counter>=limit:
            reason=f"Boshqa tomonga qarash: {counter}/{limit}" if event_type=='look_away' else f'{event_type}: {counter}/{limit}'
            freeze(conn,sid,tid)
            conn.execute("UPDATE student_test_state SET status='BLOCKED',block_reason=?,blocked_at=datetime('now') WHERE student_id=? AND test_id=?",(reason,sid,tid))
            message='Test to‘xtatildi. Administrator ruxsatini kuting.'
        elif limit>0:
            message=f'Diqqat, ekranga qarang. Ogohlantirish: {counter}/{limit}' if event_type=='look_away' else f'Ogohlantirish: {counter}/{limit}'
        result=snapshot(conn,sid,tid);result.update(message=message,event_type=event_type,counter=counter,event_limit=limit)
        return result

def resume_in_transaction(conn,sid,tid):
    conn.execute('''UPDATE camera_exam_progress SET look_count=0,epoch=epoch+1,running_since=NULL,
                    camera_status='waiting',updated_at=? WHERE student_id=? AND test_id=?''',(time.time(),sid,tid))
    conn.execute("INSERT INTO proctoring_events(student_id,test_id,event_type,details,counter) VALUES (?,?,'admin_resume','Administrator davom ettirishga ruxsat berdi',0)",(sid,tid))
