from src.main_package.example import example_function_add


def test_example_function_add():
    result = example_function_add(123, 789)
    assert result == 912
