ref: https://docs.astral.sh/uv/guides/integration/jupyter/

- to use jupyter lab with uv, we need to run `uv add --dev ipykernel` in our project dir
- and run `uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name={env_display_name}` to create jupyter kernel with same uv dependencies in the current project
- then, run `uv run --with jupyter jupyter lab`
