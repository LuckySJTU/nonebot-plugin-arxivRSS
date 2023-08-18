from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""
    arxiv_proxy: str = "http://127.0.0.1:7891"
