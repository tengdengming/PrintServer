\
    import os, subprocess, time, threading
    from typing import List, Tuple, Optional
    import win32print
    import win32con
    import win32api
    from ctypes import windll
    import config
    import tempfile

    def list_printers() -> List[str]:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        return [p[2] for p in printers]

    def _enum_spool_jobs(printer_name: str):
        """
        Return list of jobs as dictionaries for a given printer.
        """
        h = win32print.OpenPrinter(printer_name)
        try:
            # EnumJobs(hPrinter, FirstJob, NoJobs, level)
            jobs = win32print.EnumJobs(h, 0, -1, 1)
            out = []
            for j in jobs:
                out.append({
                    'JobId': j['JobId'],
                    'Document': j['pDocument'],
                    'Status': j['Status'],
                    'Position': j['Position'],
                    'TotalPages': j.get('TotalPages', None)
                })
            return out
        finally:
            win32print.ClosePrinter(h)

    def get_spool_snapshot(printer_name: str):
        try:
            return set([j['JobId'] for j in _enum_spool_jobs(printer_name)])
        except Exception:
            return set()

    def _find_new_job(printer_name: str, before_set:set, timeout:float=10.0, poll=0.5) -> Optional[int]:
        """
        After a print command, spooler will create a job. Poll spooler to find new job id.
        """
        deadline = time.time()+timeout
        while time.time() < deadline:
            after = get_spool_snapshot(printer_name)
            new = after - before_set
            if new:
                return sorted(list(new))[0]
            time.sleep(poll)
        return None

    def _wait_for_job_completion(printer_name: str, job_id:int, timeout:float=300, poll=0.8) -> Tuple[bool, dict]:
        """
        Poll job status until removed from spooler or error code appears.
        Returns (success, final_job_info)
        """
        h = win32print.OpenPrinter(printer_name)
        try:
            start = time.time()
            while True:
                try:
                    # level 1 has limited info
                    jobs = win32print.EnumJobs(h, 0, -1, 1)
                    matches = [j for j in jobs if j['JobId']==job_id]
                    if not matches:
                        # job disappeared -> assume finished successfully
                        return True, {'JobId': job_id, 'Status': 'COMPLETED'}
                    j = matches[0]
                    status = j['Status']
                    # if it has an error flag
                    if status & win32print.JOB_STATUS_ERROR:
                        return False, {'JobId': job_id, 'Status': 'ERROR', 'details': j}
                    if time.time()-start > timeout:
                        return False, {'JobId': job_id, 'Status':'TIMEOUT'}
                except Exception as e:
                    return False, {'JobId': job_id, 'Status':'EXCEPTION', 'details': str(e)}
                time.sleep(poll)
        finally:
            win32print.ClosePrinter(h)

    def _call_ghostscript_print(gs_path:str, pdf_path:str, printer_name:str, extra_args:List[str]=None) -> Tuple[int,str]:
        """
        Use GhostScript mswinpr2 device to print. Returns (exit_code, stdout+stderr)
        """
        if extra_args is None: extra_args = []
        # Compose the -sOutputFile for mswinpr2: %printer%Printer Name
        output = f"%printer%{printer_name}"
        args = [gs_path, "-dBATCH", "-dNOPAUSE", "-dNumCopies=1", "-sDEVICE=mswinpr2", f"-sOutputFile={output}"] + extra_args + [pdf_path]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
            out = proc.stdout+proc.stderr
            return proc.returncode, out
        except Exception as e:
            return -1, str(e)

    def print_pdf_and_monitor(pdf_path:str, printer_name:str, copies:int=1, detect_timeout:float=10.0, wait_timeout:float=300) -> dict:
        """
        Send PDF to GhostScript, detect spooler job, and wait for completion.
        Returns dict with status and job id.
        """
        # snapshot before
        before = get_spool_snapshot(printer_name)
        # call GS
        rc, out = _call_ghostscript_print(config.GS_PATH, pdf_path, printer_name)
        if rc != 0:
            return {'ok': False, 'error': 'ghostscript_failed', 'code': rc, 'output': out}
        # find new job
        job_id = _find_new_job(printer_name, before, timeout=config.SPOOLER_DETECT_TIMEOUT, poll=config.SPOOLER_POLL_INTERVAL)
        if job_id is None:
            # could still be printed quickly, or GS created no job; treat as unknown
            return {'ok': None, 'info': 'no_spool_job_detected', 'ghostscript_output': out}
        # wait for completion
        ok, info = _wait_for_job_completion(printer_name, job_id, timeout=wait_timeout, poll=config.SPOOLER_POLL_INTERVAL)
        return {'ok': ok, 'job_id': job_id, 'detail': info, 'ghostscript_output': out}
