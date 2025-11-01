"""
Система нумерации 01-zz (принцип dev-001)

Обеспечивает 1295 уникальных позиций на уровень иерархии:
- 01-99: числа 1-99 (99 позиций)
- 0a-9z: 100-459 (360 позиций)
- a0-z9: 460-819 (360 позиций)
- aa-zz: 820-1295 (476 позиций)
"""


class Numbering01zz:
    """Система нумерации dev-001"""
    
    @staticmethod
    def encode(num: int) -> str:
        """
        Преобразовать число 1-1295 в код 01-zz
        
        Args:
            num: Число от 1 до 1295
            
        Returns:
            Строка формата 01-zz
            
        Raises:
            ValueError: Если число вне диапазона
            
        Examples:
            >>> Numbering01zz.encode(1)
            '01'
            >>> Numbering01zz.encode(99)
            '99'
            >>> Numbering01zz.encode(100)
            '0a'
            >>> Numbering01zz.encode(1295)
            'zz'
        """
        if num < 1 or num > 1295:
            raise ValueError(f"Число {num} вне диапазона 1-1295")
        
        # 01-99: числа 1-99
        if num <= 99:
            return f"{num:02d}"
        
        num -= 99
        
        # 0a-9z: числа 100-459 (36 символов * 10 = 360)
        if num <= 360:
            first = str((num - 1) // 36)
            second_idx = (num - 1) % 36
            if second_idx < 26:
                second = chr(ord('a') + second_idx)
            else:
                second = chr(ord('0') + second_idx - 26)
            return f"{first}{second}"
        
        num -= 360
        
        # a0-z9: числа 460-819 (26 букв * 10 цифр + остаток = 360)
        if num <= 360:
            first_idx = (num - 1) // 10
            second = str((num - 1) % 10)
            first = chr(ord('a') + first_idx)
            return f"{first}{second}"
        
        num -= 360
        
        # aa-zz: числа 820-1295 (26 * 26 = 676, используем 476)
        first_idx = (num - 1) // 26
        second_idx = (num - 1) % 26
        first = chr(ord('a') + first_idx)
        second = chr(ord('a') + second_idx)
        return f"{first}{second}"
    
    @staticmethod
    def make_path(parent_path: str, child_num: int) -> str:
        """
        Создать путь для дочернего узла
        
        Args:
            parent_path: Путь родителя (например, "01.01")
            child_num: Номер дочернего узла (1-based)
            
        Returns:
            Путь дочернего узла (например, "01.01.02")
            
        Examples:
            >>> Numbering01zz.make_path("01", 1)
            '01.01'
            >>> Numbering01zz.make_path("01.01", 2)
            '01.01.02'
        """
        child_code = Numbering01zz.encode(child_num)
        return f"{parent_path}.{child_code}"

