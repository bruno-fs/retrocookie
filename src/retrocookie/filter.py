"""Interface for git-filter-repo."""
from pathlib import Path
from typing import Any
from typing import Container
from typing import Dict
from typing import List
from typing import Tuple

from git_filter_repo import Blob
from git_filter_repo import FilteringOptions
from git_filter_repo import RepoFilter

from . import git
from . import utils


def get_replacements(
    context: Dict[str, str], whitelist: Container[str], blacklist: Container[str],
) -> List[Tuple[str, str]]:
    """Return replacements to be applied to commits from the template instance."""

    def ref(key: str) -> str:
        return f"{{{{ cookiecutter.{key} }}}}"

    escape = [(token, token.join(('{{ "', '" }}'))) for token in ("{{", "}}")]
    replacements = [
        (value, ref(key))
        for key, value in context.items()
        if key not in blacklist and not (whitelist and key not in whitelist)
    ]

    return escape + replacements


class RepositoryFilter:
    """Perform path and blob replacements on a repository."""

    def __init__(
        self,
        repository: git.Repository,
        path: Path,
        context: Dict[str, str],
        whitelist: Container[str],
        blacklist: Container[str],
    ) -> None:
        """Initialize."""
        self.repository = repository
        self.path = str(path).encode()
        self.replacements = [
            (old.encode(), new.encode())
            for old, new in get_replacements(context, whitelist, blacklist)
        ]

    def filename_callback(self, filename: bytes) -> bytes:
        """Rewrite filenames."""
        for old, new in self.replacements:
            filename = filename.replace(old, new)
        return b"/".join((self.path, filename))

    def blob_callback(self, blob: Blob, metadata: Dict[str, Any]) -> None:
        """Rewrite blobs."""
        for old, new in self.replacements:
            blob.data = blob.data.replace(old, new)

    def _create_filter(self) -> RepoFilter:
        """Create the filter."""
        args = FilteringOptions.parse_args([], error_on_empty=False)
        return RepoFilter(
            args,
            filename_callback=self.filename_callback,
            blob_callback=self.blob_callback,
        )

    def run(self) -> None:
        """Run the filter."""
        with utils.chdir(self.repository.path):
            repofilter = self._create_filter()
            repofilter.run()
