import os, time, uuid, shutil, threading, json, tempfile
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import config, models, printer
from typing import Dict

app = FastAPI(title="Remote Print Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# simple in-memory job store. For production use a persistent DB.
JOBS: Dict[str, Dict] = {}

def require_token(request: Request):
    token = request.headers.get('X-API-Token') or request.query_params.get('token')
    if token != config.API_TOKEN:
        raise HTTPException(status_code=401, detail='unauthorized')

@app.get('/printers')
def api_printers(request: Request):
    require_token(request)
    try:
        printers = printer.list_printers()
        return JSONResponse({'printers': printers})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/files')
def api_files(request: Request, path: str = ''):
    require_token(request)
    base = os.path.normpath(config.BASE_DIR)
    target = os.path.normpath(os.path.join(base, path))
    if not target.startswith(base):
        raise HTTPException(status_code=400, detail='invalid path')
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail='not found')
    items = []
    if os.path.isdir(target):
        for name in sorted(os.listdir(target)):
            p = os.path.join(target, name)
            items.append({
                'name': name,
                'path': os.path.relpath(p, base).replace('\\','/'),
                'is_dir': os.path.isdir(p),
                'size': os.path.getsize(p) if os.path.isfile(p) else None
            })
    else:
        items.append({
            'name': os.path.basename(target),
            'path': os.path.relpath(target, base).replace('\\','/'),
            'is_dir': False,
            'size': os.path.getsize(target)
        })
    return JSONResponse(items)

@app.post('/print')
async def api_print(request: Request, background_tasks: BackgroundTasks):
    require_token(request)
    body = await request.json()
    try:
        pr = models.PrintRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    base = os.path.normpath(config.BASE_DIR)
    path = os.path.normpath(os.path.join(base, pr.path))
    if not path.startswith(base) or not os.path.exists(path):
        raise HTTPException(status_code=404, detail='file not found')

    # create job id and store
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {'status':'queued', 'created': time.time(), 'request': pr.dict()}

    def run_job(jid, req: models.PrintRequest):
        JOBS[jid]['status'] = 'running'
        try:
            # If file is not PDF, we convert using GhostScript or let Windows handle - here we assume input PDF.
            # For production, add conversion for office formats via LibreOffice or Word COM.
            pdf_path = path
            res = printer.print_pdf_and_monitor(pdf_path, req.printer or printer.get_default_printer(), copies=req.copies)
            JOBS[jid]['result'] = res
            JOBS[jid]['status'] = 'done' if res.get('ok') else 'failed'
        except Exception as e:
            JOBS[jid]['status'] = 'failed'
            JOBS[jid]['result'] = {'error': str(e)}

    background_tasks.add_task(run_job, job_id, pr)
    return JSONResponse({'job_id': job_id, 'status': 'queued'})

@app.get('/job/{job_id}')
def api_job(request: Request, job_id: str):
    require_token(request)
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='not found')
    return JSONResponse(job)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8899, reload=False)
