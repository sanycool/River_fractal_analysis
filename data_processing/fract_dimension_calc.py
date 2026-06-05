import numpy as np
from scipy import stats


def coords_to_log(x_coordinates, y_coordinates):
    # Преобразуем списки в numpy массивы
    x = np.array(x_coordinates)
    y = np.array(y_coordinates)

    # Находим пары элементов, которые больше 0, чтобы избежать проблем с log(0) и log(отрицательное)
    valid_indices = (x > 0) & (y > 0)

    # Фильтруем только валидные данные
    x_valid = x[valid_indices]
    y_valid = y[valid_indices]

    if len(x_valid) < 2 or len(y_valid) < 2:
        print("Недостаточно валидных данных, пропуск.")
        return [None], [None]

    # Применяем логарифмическое преобразование к координатам
    log_x = np.log10(x_valid)
    log_y = np.log10(y_valid)

    return log_x, log_y


def fract_dimension_finder(x_coordinates, y_coordinates):

    # Линейная регрессия
    slope, intercept, r_value, p_value, std_error = stats.linregress(x_coordinates, y_coordinates)

    # Вычисление R^2
    r_squared = r_value ** 2

    return slope, r_squared, std_error
