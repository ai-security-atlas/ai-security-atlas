"""local-hub: a local, git-backed stand-in for a model hub (imported as `import local_hub`).

Founded by LAB-10 attack-dependency, generalizing LAB-01's bare-git hub (Step 8 / D1).
PYTHONPATH=/labs/_shared is set on the workbench and sandbox services, so any lab script can
`import local_hub`. Nothing here touches the network: every repo is a bare git repository under
a folder you pass in (normally `labkit.work() / "hub"`), and every remote URL is asserted to be
a local path.

Layout (mirrors the Hugging Face Hub and its cache):

    <root>/<org>/<name>.git                     bare repo; branches and tags are hub revisions
    <root>/.clones/<org>/<name>                 the publisher's working clone (push())
    <root>/snapshots/<org>--<name>/<sha>/       a checkout of one commit, no .git (snapshot())

`snapshot(repo_id, revision)` resolves a branch, tag or commit to a full sha and checks that
commit out into its own folder, like `huggingface_hub.snapshot_download(revision=...)`. Pass the
folder to `from_pretrained()`; transformers ignores `revision=` for a local folder, so the hub
resolves it.

Determinism. Commits use fixed author and committer dates (`BASE_DATE` plus one hour per commit
already in the repo) and fixed identities, so the same files pushed in the same order give the
same commit shas on every machine. Labs may print and pin those shas (LAB-10 does). Keep the
file bytes deterministic too: write safetensors from exact values, never torch.save() (its
`.data/serialization_id` is random per save).

Typical use:

    import labkit, local_hub
    hub = local_hub.Hub(labkit.work() / "hub")
    hub.create("acme/tiny-sentiment")
    sha = hub.push("acme/tiny-sentiment", {"config.json": "...", "model.safetensors": b"..."},
                   "publish v1.0", tag="v1.0")
    hub.tag("acme/tiny-sentiment", "v1.0", other_sha, force=True)   # an attacker moves a tag
    folder, sha = hub.snapshot("acme/tiny-sentiment", "main")
    local_hub.manifest(folder)                                       # {file: sha256}

Every git call is non-interactive (stdin closed, no gpg signing, GIT_TERMINAL_PROMPT=0).
The read-only helpers (resolve, log, diff, files, show, snapshot) work on a read-only checkout,
for example in the sandbox service, as long as `snapshots_root` points at a writable folder.
"""

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

BASE_DATE = 1767607200  # 2026-01-05 10:00:00 UTC; commit n is BASE_DATE + n hours
SHA = re.compile(r"[0-9a-f]{40}")


def is_sha(rev) -> bool:
    """True only for a full 40-hex commit id (a branch or tag name can move; a sha cannot)."""
    return bool(SHA.fullmatch(str(rev)))


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(data) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(folder) -> dict:
    """{file name: sha256} for the files directly in a folder (no recursion, no dot files)."""
    return {p.name: sha256(p) for p in sorted(Path(folder).iterdir())
            if p.is_file() and not p.name.startswith(".")}


def git(*args, cwd=None, who="acme", date=None, env=None, check=True) -> str:
    """Run one non-interactive git command and return its stdout (stripped)."""
    cmd = ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "init.defaultBranch=main",
           "-c", "core.autocrlf=false", "-c", f"user.name={who}", "-c", f"user.email={who}@hub.invalid", *args]
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", **(env or {}))
    if date is not None:
        stamp = f"@{int(date)} +0000"
        env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.rstrip()


class Hub:
    """A folder of bare git repos named <org>/<name>.git."""

    def __init__(self, root, snapshots_root=None):
        self.root = Path(root)
        self.snapshots = Path(snapshots_root) if snapshots_root else self.root / "snapshots"

    # ---- repos
    def repo(self, repo_id) -> Path:
        org, name = self._split(repo_id)
        return self.root / org / f"{name}.git"

    def exists(self, repo_id) -> bool:
        return (self.repo(repo_id) / "HEAD").exists()

    def create(self, repo_id) -> Path:
        """(Re)create an empty bare repo, dropping any old clone and snapshots of it."""
        org, name = self._split(repo_id)
        bare = self.repo(repo_id)
        for d in (bare, self._clone_dir(repo_id), self.snapshots / f"{org}--{name}"):
            shutil.rmtree(d, ignore_errors=True)
        bare.parent.mkdir(parents=True, exist_ok=True)
        git("init", "-q", "--bare", str(bare))
        return bare

    def push(self, repo_id, files, message, who="acme", branch="main", tag=None, remove=()) -> str:
        """Commit `files` ({path: str | bytes}) and delete `remove` on `branch`, push, return the sha.

        `who` is the committer name; with push access anyone can commit as anyone, which is
        the point of the substitution labs."""
        bare = self.repo(repo_id)
        work = self._clone_dir(repo_id)
        if not work.exists():
            work.parent.mkdir(parents=True, exist_ok=True)
            git("clone", "-q", str(bare), str(work))
            remote = git("remote", "get-url", "origin", cwd=work)
            assert remote.startswith("/") and Path(remote) == bare, f"hub remote must be a local path, got {remote}"
        else:
            git("fetch", "-q", "--tags", "--force", "origin", cwd=work)
        has_branch = bool(git("ls-remote", "--heads", str(bare), branch, cwd=work))
        if has_branch:
            git("checkout", "-q", "-B", branch, f"origin/{branch}", cwd=work)
        else:
            git("checkout", "-q", "--orphan", branch, cwd=work)
        for rel, data in files.items():
            p = work / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(data, str):
                data = data.encode("utf-8")
            p.write_bytes(data)
        for rel in remove:
            git("rm", "-q", "--", rel, cwd=work)
        git("add", "-A", cwd=work)
        n = int(git("rev-list", "--all", "--count", cwd=work) or 0)
        git("commit", "-q", "-m", message, cwd=work, who=who, date=BASE_DATE + 3600 * n)
        git("push", "-q", "origin", branch, cwd=work)
        sha = git("rev-parse", "HEAD", cwd=work)
        if tag:
            self.tag(repo_id, tag, sha)
        return sha

    def tag(self, repo_id, name, rev, force=False) -> str:
        """Point a (lightweight) tag at rev. force=True moves an existing tag, as an attacker with
        push access can (`git push --force origin <tag>`)."""
        sha = self.resolve(repo_id, rev)
        git("tag", *(["-f"] if force else []), name, sha, cwd=self.repo(repo_id))
        return sha

    # ---- read-only helpers
    def resolve(self, repo_id, rev) -> str:
        """Full commit sha of a branch, tag or (short or full) sha; "" if unknown."""
        return git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", cwd=self.repo(repo_id), check=False)

    def refs(self, repo_id) -> dict:
        """{'main': sha, 'v1.0': sha, ...} for every branch and tag."""
        out = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads", "refs/tags",
                  cwd=self.repo(repo_id))
        return dict(line.split(" ", 1) for line in out.splitlines() if line)

    def log(self, repo_id, ref="main"):
        """[(short sha, committer, subject), ...], newest first."""
        out = git("log", "--format=%h%x09%cn%x09%s", ref, cwd=self.repo(repo_id))
        return [tuple(line.split("\t", 2)) for line in out.splitlines()]

    def files(self, repo_id, rev):
        return git("ls-tree", "-r", "--name-only", rev, cwd=self.repo(repo_id)).splitlines()

    def show(self, repo_id, rev, path) -> bytes:
        p = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=self.repo(repo_id), capture_output=True,
                           stdin=subprocess.DEVNULL, check=True)
        return p.stdout

    def diff(self, repo_id, a, b, *paths, stat=False) -> str:
        return git("diff", "--stat" if stat else "--unified=1", "-M", a, b, "--", *paths, cwd=self.repo(repo_id))

    def snapshot(self, repo_id, revision="main"):
        """Check out one commit into snapshots/<org>--<name>/<sha>/ (no .git). Returns (folder, sha)."""
        sha = self.resolve(repo_id, revision)
        if not sha:
            raise ValueError(f"{repo_id}: unknown revision {revision!r}")
        org, name = self._split(repo_id)
        dest = self.snapshots / f"{org}--{name}" / sha
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        index = dest.with_name(sha + ".index")  # a private index, so a read-only repo is never written
        env = {"GIT_INDEX_FILE": str(index)}
        bare = str(self.repo(repo_id))
        git("--git-dir", bare, "--work-tree", str(dest), "read-tree", sha, env=env)
        git("--git-dir", bare, "--work-tree", str(dest), "checkout-index", "-a", "-f", env=env)
        index.unlink(missing_ok=True)
        return dest, sha

    # ---- internals
    @staticmethod
    def _split(repo_id):
        org, sep, name = str(repo_id).partition("/")
        if not sep or not org or not name or "/" in name or ".." in repo_id:
            raise ValueError(f"repo id must look like 'org/name', got {repo_id!r}")
        return org, name

    def _clone_dir(self, repo_id) -> Path:
        org, name = self._split(repo_id)
        return self.root / ".clones" / org / name
