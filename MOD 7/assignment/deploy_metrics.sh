#!/bin/bash
# deploy_metrics.sh -- Measured evidence for the "ease of deployment" criterion.
echo "=============================================================="
echo "DEPLOYMENT ARTIFACT COMPARISON"
echo "=============================================================="
echo
echo "-- Go: single static binary --"
GOBIN="gobench/gobench"
echo "  binary size            $(du -h "$GOBIN" | cut -f1)"
echo "  dynamic dependencies:"
otool -L "$GOBIN" 2>/dev/null | tail -n +2 | sed 's/^/    /'
echo "  runtime required on target host: none (self-contained)"
echo
echo "-- Python: interpreter + stdlib + site-packages --"
PYBIN=$(command -v python3)
PYPREFIX=$(python3 -c "import sys; print(sys.base_prefix)")
echo "  interpreter binary     $(du -h "$PYBIN" 2>/dev/null | cut -f1)"
echo "  stdlib directory       $(du -sh "$(python3 -c 'import sysconfig;print(sysconfig.get_paths()["stdlib"])')" 2>/dev/null | cut -f1)"
echo "  numpy (one dependency) $(python3 -c "import numpy,os,pathlib;print(sum(f.stat().st_size for f in pathlib.Path(numpy.__path__[0]).rglob('*') if f.is_file())//1048576)" 2>/dev/null)MB"
echo "  runtime required on target host: matching CPython + all deps"
echo
echo "-- Cold start (process launch to first line of work) --"
python3 - <<'PYEOF'
import subprocess, time, statistics, os
def bench(cmd, n=15):
    xs=[]
    for _ in range(n):
        t=time.perf_counter(); subprocess.run(cmd, capture_output=True); xs.append((time.perf_counter()-t)*1000)
    return statistics.median(xs)
go_ms = bench(["gobench/gobench","--help"])
py_ms = bench(["python3","-c","pass"])
py_np = bench(["python3","-c","import numpy"])
print(f"  Go binary startup            {go_ms:7.2f} ms  (median of 15)")
print(f"  python3 -c pass              {py_ms:7.2f} ms  (median of 15)")
print(f"  python3 -c 'import numpy'    {py_np:7.2f} ms  (median of 15)")
print(f"  -> Python interpreter start is {py_ms/go_ms:.1f}x Go's; with numpy {py_np/go_ms:.1f}x")
PYEOF
