"""Check Git upload candidates and test a source-only copy without touching the real Git index."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

PROJECT=Path(__file__).resolve().parents[1]
REPOSITORY=PROJECT.parent
FORBIDDEN={'.venv','.dart_tool','build','ephemeral','__pycache__','.aws','.codex','.agents','.idea'}


def main():
    out=PROJECT/'results/handoff';out.mkdir(exist_ok=True)
    report_path=out/'source_checkout.json'
    manifest_path=out/'source_manifest.txt'
    log_path=out/'source_checkout_tests.txt'
    for path in (report_path,manifest_path,log_path):
        if not path.exists():path.touch()
    with tempfile.TemporaryDirectory(prefix='fourier-source-check-') as temporary:
        temp=Path(temporary)
        index=temp/'index'
        subprocess.run(['git','init','--quiet',str(index)],check=True)
        command=['git',f'--git-dir={index}/.git',f'--work-tree={REPOSITORY}']
        listed=subprocess.run(command+['ls-files','--others','--exclude-standard','-z'],
                              cwd=REPOSITORY,check=True,capture_output=True).stdout
        files=sorted(name.decode('utf-8') for name in listed.split(b'\0') if name)
        assert files, 'No source candidates found'
        for name in files:
            assert not FORBIDDEN.intersection(Path(name).parts), name
        required=['README.md','.gitignore','goi2/flutter_app/pubspec.lock',
          'goi2/flutter_app/assets/fonts/DejaVuSans.ttf','goi2/results/demo/noisy.png',
          'goi2/results/handoff/verification.json','goi2/docs/DOI_CHIEU_NHIEM_VU.md']
        for name in required:assert name in files, f'Missing source candidate: {name}'
        # Actual Git ignore rules, using an isolated temporary index.
        ignored=['.aws/test','goi2/.venv/test','goi2/flutter_app/build/test',
                 'goi2/flutter_app/.dart_tool/test','goi2/results/my_run/filtered.png',
                 'goi2/results/mask_hand/filtered.png']
        for name in ignored:
            check=subprocess.run(command+['check-ignore','--quiet',name],cwd=REPOSITORY)
            assert check.returncode==0, f'Not ignored: {name}'
        fresh=temp/'checkout'
        for name in files:
            source=REPOSITORY/name
            assert source.is_file() and not source.is_symlink(),name
            target=fresh/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
        assert not (fresh/'goi2/.venv').exists()
        assert not (fresh/'goi2/flutter_app/build').exists()
        runtime=sys.executable
        tests=subprocess.run([runtime,'-m','unittest','discover','-s','tests','-v'],
          cwd=fresh/'goi2',capture_output=True,text=True)
        cli=subprocess.run([runtime,'-m','frequency_filter','results/demo/noisy.png',
          '--filter','auto','--padding','none','--radius','3','--kind','butterworth',
          '--output',str(temp/'cli_result')],cwd=fresh/'goi2',capture_output=True,text=True)
        log_path.write_text(tests.stdout+tests.stderr+'\nCLI:\n'+cli.stdout+cli.stderr,encoding='utf-8')
        report={'scope':'Simulated source-only Git checkout using actual ignore rules; no remote access',
          'source_files':len(files),'total_source_bytes':sum((REPOSITORY/name).stat().st_size for name in files),
          'required_files_present':True,'generated_and_private_paths_ignored':ignored,
          'python_tests_exit_code':tests.returncode,'cli_exit_code':cli.returncode,
          'cli_output_created':(temp/'cli_result/filtered.png').is_file(),
          'dependency_note':'Uses the existing Python runtime for NumPy/Pillow; does not test a fresh pip installation',
          'flutter_note':'Flutter checks are recorded separately in flutter_review.json'}
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        manifest_path.write_text('\n'.join(files)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2))
        assert tests.returncode==0 and cli.returncode==0 and report['cli_output_created'], 'Source-only verification failed'


if __name__=='__main__':main()
