import time
from config import Z_SCORE_CHANGE_THRESHOLD, PERCENTAGE_CHANGE_THRESHOLD

class SignalStateManager:
    def __init__(self):
        self.last_signals = {}

    def has_significant_change(self, current_signal, previous_signal):
        """
        检查新信号与上一个信号相比是否有显著变化。
        """
        if not previous_signal:
            return True

        # 检查Z-Score类型的信号
        if 'z_score' in current_signal['primary_signal'] and 'z_score' in previous_signal['primary_signal']:
            try:
                new_z = float(current_signal['primary_signal']['z_score'])
                old_z = float(previous_signal['primary_signal']['z_score'])
                if abs(new_z - old_z) >= Z_SCORE_CHANGE_THRESHOLD:
                    return True
            except (ValueError, TypeError):
                # 如果转换失败，则忽略此检查
                pass

        # 检查百分比类型的信号 (例如 OI 变化)
        # 查找包含 'change' 的键 (如 'change_24h', 'change_1_period')
        change_keys = [k for k in current_signal['primary_signal'].keys() if 'change' in k]
        for key in change_keys:
            if key in previous_signal['primary_signal']:
                try:
                    # 移除 % 并转换为 float (e.g., "+5.20%" -> 0.052)
                    new_val_str = current_signal['primary_signal'][key].replace('%', '').replace('+', '')
                    old_val_str = previous_signal['primary_signal'][key].replace('%', '').replace('+', '')
                    
                    new_change = float(new_val_str) / 100
                    old_change = float(old_val_str) / 100
                    
                    if abs(new_change - old_change) >= PERCENTAGE_CHANGE_THRESHOLD:
                        return True
                except (ValueError, TypeError):
                    continue

        # 默认情况下，如果没有特定逻辑匹配，则认为没有显著变化
        # 这可以防止对同一事件的重复、无价值的警报
        return False

    def should_send_alert(self, symbol, signal):
        """
        判断是否应该发送警报。
        只在信号与上次同类型信号有显著差异时才发送。
        """
        indicator_type = signal['primary_signal']['indicator']
        signal_key = f"{symbol}_{indicator_type}"

        previous_signal = self.last_signals.get(signal_key)

        if self.has_significant_change(signal, previous_signal):
            self.last_signals[signal_key] = signal
            return True, previous_signal
        
        return False, previous_signal
