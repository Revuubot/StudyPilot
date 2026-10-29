import pytest
from unittest.mock import MagicMock
from tasks import _update_task_status

def test_update_task_status():
    db = MagicMock()
    task = MagicMock()
    db.query().filter().first.return_value = task
    
    _update_task_status(db, "t1", "done", result="success")
    
    assert task.status == "done"
    assert task.result == "success"
    db.commit.assert_called_once()
