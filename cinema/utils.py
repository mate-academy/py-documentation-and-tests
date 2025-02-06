def params_to_ints(qs):
    """Конвертируем строку '1,2,3' в список [1, 2, 3]"""
    return [int(str_id) for str_id in qs.split(",")]
