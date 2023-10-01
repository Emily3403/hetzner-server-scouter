from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.crud import create_simple_model


def test_create_simple_model_with_author(db: DatabaseSession) -> None:
    description = "test_description"
    author = "Emily"

    it = create_simple_model(db, description, author)
    assert it is not None
    assert it.description == description
    assert it.optional_author == author


def test_create_simple_model_without_author(db: DatabaseSession) -> None:
    description = "test_description"  #

    it = create_simple_model(db, description)
    assert it is not None
    assert it.description == description
    assert it.optional_author is None
