import pytest
from fastapi_async_lib.engine.state_machine import (
    create_task_state_machine,
    TransitionError,
)


def test_valid_transition_flow():
    """测试标准合法路径：pending -> running -> done"""
    # 1. 创建状态机
    sm = create_task_state_machine()

    # 2. 验证初始状态
    assert sm.get_state() == "pending"

    # 3. 执行合法转换：pending -> running
    assert sm.transition_to("running") is True
    assert sm.get_state() == "running"

    # 3. 执行合法转换：running -> done
    assert sm.transition_to("done") is True
    assert sm.get_state() == "done"


def test_invalid_transition_raise():
    """测试非法转换：pending 不能直接跳到 done（必须经过 running）"""
    sm = create_task_state_machine()

    # 使用 pytest.raises 上下文管理器，断言会抛出 TransitionError
    with pytest.raises(TransitionError, match="不允许从 pending 转换到 done"):
        sm.transition_to("done")

    # 额外验证：状态机没有被修改，依然停留在 pending
    assert sm.get_state() == "pending"


def test_rest_change_current_state():
    """测试 reset 可以强行改变状态机的当前状态"""
    sm = create_task_state_machine()

    assert sm.get_state() == "pending"
    sm.transition_to("running")
    assert sm.get_state() == "running"

    # 强制重置为 pending
    sm.reset("pending")
    assert sm.get_state() == "pending"

    # 重置后，原本 running 才能走的路径现在不能走了
    with pytest.raises(TransitionError, match="不允许从 pending 转换到 done"):
        sm.transition_to("done")

    # 但 pending -> running 依然可以
    sm.transition_to("running")
    assert sm.get_state() == "running"
