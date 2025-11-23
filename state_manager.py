import time
from config import SIGNAL_COOLDOWN_PERIOD, Z_SCORE_CHANGE_THRESHOLD, PERCENTAGE_CHANGE_THRESHOLD

class SignalStateManager:
    def __init__(self):
        """
        初始化信号状态管理器，用于存储已发送信号的状态以避免重复。
        """
        # 存储结构: { "unique_key": {"timestamp": float, "signal_data": dict} }
        # unique_key 示例: "DOGEUSDT-LSRatioSignal-Sentiment Extreme Alert"
        self.last_triggered_signals = {}

    def _get_unique_key(self, symbol, signal):
        """
        根据币种、指标名称和信号类型生成唯一的键。
        """
        indicator = signal['primary_signal'].get('indicator', 'UnknownIndicator')
        signal_type = signal['primary_signal'].get('signal_type', 'UnknownType')
        return f"{symbol}-{indicator}-{signal_type}"

    def should_send_alert(self, symbol, signal):
        """
        判断是否应该发送新的警报。
        返回一个元组 (should_send: bool, previous_signal: dict | None)
        """
        unique_key = self._get_unique_key(symbol, signal)
        current_time = time.time()
        
        last_signal_info = self.last_triggered_signals.get(unique_key)

        # 1. 如果之前从未发送过此信号，则应发送
        if not last_signal_info:
            print(f"[State Manager] 新的信号类型 {unique_key}，允许发送。")
            self._update_state(unique_key, signal)
            return True, None

        last_timestamp = last_signal_info['timestamp']
        last_signal_data = last_signal_info['signal_data']['primary_signal']
        
        # 2. 检查是否已超过冷却期
        if (current_time - last_timestamp) / 60 > SIGNAL_COOLDOWN_PERIOD:
            print(f"[State Manager] 信号 {unique_key} 已超过冷却期，允许发送。")
            self._update_state(unique_key, signal)
            return True, last_signal_data
            
        # 3. 在冷却期内，检查信号是否有显著变化
        current_signal_data = signal['primary_signal']

        # 3a. 对于 Z-Score 类信号
        if 'z_score' in current_signal_data:
            try:
                last_z = float(last_signal_data.get('z_score', 0))
                current_z = float(current_signal_data.get('z_score', 0))
                if abs(current_z - last_z) > Z_SCORE_CHANGE_THRESHOLD:
                    print(f"[State Manager] 信号 {unique_key} 的 Z-Score 变化显著 ({last_z:.2f} -> {current_z:.2f})，允许发送。")
                    self._update_state(unique_key, signal)
                    return True, last_signal_data
            except (ValueError, TypeError):
                pass # 如果z_score不是数字，则忽略

        # 3b. 对于百分比变化类信号 (例如 OI 24小时变化)
        if 'change_24h' in current_signal_data:
            try:
                # 从字符串 'xx.xx%' 转换回浮点数
                last_change_str = last_signal_data.get('change_24h', '0%').strip('%')
                current_change_str = current_signal_data.get('change_24h', '0%').strip('%')
                last_change = float(last_change_str) / 100
                current_change = float(current_change_str) / 100
                if abs(current_change - last_change) > PERCENTAGE_CHANGE_THRESHOLD:
                    print(f"[State Manager] 信号 {unique_key} 的百分比变化显著 ({last_change:.2%} -> {current_change:.2%})，允许发送。")
                    self._update_state(unique_key, signal)
                    return True, last_signal_data
            except (ValueError, TypeError):
                pass

        print(f"[State Manager] 信号 {unique_key} 在冷却期内且无显著变化，已抑制。")
        return False, last_signal_data

    def _update_state(self, unique_key, signal):
        """
        更新或创建信号的状态。
        """
        self.last_triggered_signals[unique_key] = {
            "timestamp": time.time(),
            "signal_data": signal
        }
