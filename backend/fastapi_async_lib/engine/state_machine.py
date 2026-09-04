from typing import Optional, Set, Dict, Callable, Any
from dataclasses import dataclass


class TransitionError(Exception):
    """状态转换非法时抛出的异常"""

    pass


@dataclass
class StateTransition:
    """定义一次状态转换"""

    from_state: str
    to_state: str
    allowed: bool
    on_transition: Optional[Callable] = None


class StateMachine:
    """
    通用状态机

    职责：
    1. 定义状态转换规则（哪些状态可以转到哪些状态）
    2. 执行状态转换（验证合法性 + 执行回调）
    3. 查询当前状态和可用转换
    """

    def __init__(self, initial_state: str):
        self._state = initial_state
        self._transitions: Dict[str, Dict[str, StateTransition]] = {}
        self._on_state_change: Optional[Callable[[str, str], None]] = None

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        on_transition: Optional[Callable] = None,
    ) -> "StateMachine":
        """
        添加一个允许的状态转换

        Args:
            from_state: 源状态
            to_state: 目标状态
            on_transition: 转换时的回调函数
        """
        if from_state not in self._transitions:
            self._transitions[from_state] = {}
        self._transitions[from_state][to_state] = StateTransition(
            from_state=from_state,
            to_state=to_state,
            allowed=True,
            on_transition=on_transition,
        )
        return self

    def add_transitions(self, transitions: list[tuple[str, str]]) -> "StateMachine":
        """批量添加转换"""
        for from_state, to_state in transitions:
            self.add_transition(from_state, to_state)
        return self

    def on_state_change(self, callback: Callable[[str, str], None]) -> "StateMachine":
        """注册状态变更监听器"""
        self._on_state_change = callback
        return self

    def transition_to(self, new_state: str, context: Any = None) -> bool:
        """
        执行状态转换

        Args:
            new_state: 目标状态
            context: 传递给回调函数的上下文
        Returns:
            bool: 转换是否成功
        Raises:
            TransitionError: 如果转换非法
        """
        # 1. 检查是否为目标状态
        if self._state == new_state:
            return True

        # 2. 检查转换是否允许
        from_transitions = self._transitions.get(self._state, {})
        transition = from_transitions.get(new_state)

        if not transition or not transition.allowed:
            raise TransitionError(f"不允许从 {self._state} 转换到 {new_state}")

        old_state = self._state

        # 3. 执行转换回调
        if transition.on_transition:
            transition.on_transition(old_state, new_state, context)

        # 4. 更新状态
        self._state = new_state

        # 5. 触发全局监听器
        if self._on_state_change:
            self._on_state_change(old_state, new_state)

        return True

    def can_transition_to(self, new_state: str) -> bool:
        """检查是否可以转换到目标状态"""
        from_transitions = self._transitions.get(self._state, {})
        return new_state in from_transitions and from_transitions[new_state].allowed

    def get_state(self) -> str:
        """获取当前状态"""
        return self._state

    def get_available_transitions(self) -> Set[str]:
        """获取所有可用的目标状态"""
        from_transitions = self._transitions.get(self._state, {})
        return {t.to_state for t in from_transitions.values() if t.allowed}

    def reset(self, initial_state: str) -> None:
        """重置状态机"""
        self._state = initial_state


# ---------- 预定义状态机工厂 ----------
def create_task_state_machine() -> StateMachine:
    """
    创建任务状态机（预设任务状态流转规则）

    状态流转图：
    pending → running → done
    pending → running → failed
    pending → running → cancelled
    pending → cancelled
    """
    sm = StateMachine(initial_state="pending")

    # 允许的状态转换
    sm.add_transitions(
        [
            # pending → running/cancelled
            ("pending", "running"),
            ("pending", "cancelled"),
            # running → 终态
            ("running", "done"),
            ("running", "failed"),
            ("running", "cancelled"),
        ]
    )
    return sm


# ---------- 状态常量 ----------
class TaskState:
    """任务状态常量（与 BaseTaskStatus 对齐）"""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # 终态集合
    TERMINAL_STATES = {DONE, FAILED, CANCELLED}

    # 活跃状态集合
    ACTIVE_STATES = {PENDING, RUNNING}

    @classmethod
    def is_terminal(cls, state: str) -> bool:
        return state in cls.TERMINAL_STATES

    @classmethod
    def is_active(cls, state: str) -> bool:
        return state in cls.ACTIVE_STATES
