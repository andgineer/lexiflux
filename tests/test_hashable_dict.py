import pytest
import allure
from lexiflux.language.llm import Llm


@pytest.fixture
def llm():
    return Llm()


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test simple dictionary')
def test_hashable_dict_simple(llm):
    input_dict = {"a": 1, "b": "string", "c": 3.14}
    result = llm._hashable_dict(input_dict)
    expected = (("a", 1), ("b", "string"), ("c", 3.14))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with list')
def test_hashable_dict_with_list(llm):
    input_dict = {"a": [1, 2, 3], "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", (1, 2, 3)), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with nested dict')
def test_hashable_dict_with_nested_dict(llm):
    input_dict = {"a": {"nested": "value"}, "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", (("nested", "value"),)), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with nested list of dicts')
def test_hashable_dict_with_nested_list_of_dicts(llm):
    input_dict = {"a": [{"x": 1}, {"y": 2}], "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", ((("x", 1),), (("y", 2),))), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with complex nesting')
def test_hashable_dict_with_complex_nesting(llm):
    input_dict = {
        "a": [1, {"nested": [2, 3, {"deep": "value"}]}, 4],
        "b": {"x": [5, 6], "y": {"z": 7}}
    }
    result = llm._hashable_dict(input_dict)
    expected = (
        ("a", (1, (("nested", (2, 3, (("deep", "value"),))),), 4)),
        ("b", (("x", (5, 6)), ("y", (("z", 7),))))
    )
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test empty dictionary')
def test_hashable_dict_empty(llm):
    input_dict = {}
    result = llm._hashable_dict(input_dict)
    expected = ()
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with None value')
def test_hashable_dict_with_none(llm):
    input_dict = {"a": None, "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", None), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with tuple')
def test_hashable_dict_with_tuple(llm):
    input_dict = {"a": (1, 2, 3), "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", (1, 2, 3)), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary sorting')
def test_hashable_dict_sorting(llm):
    input_dict = {"c": 3, "a": 1, "b": 2}
    result = llm._hashable_dict(input_dict)
    expected = (("a", 1), ("b", 2), ("c", 3))
    assert result == expected

@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with empty list')
def test_hashable_dict_with_empty_list(llm):
    input_dict = {"a": [], "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", ()), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with empty nested dict')
def test_hashable_dict_with_empty_nested_dict(llm):
    input_dict = {"a": {}, "b": "string"}
    result = llm._hashable_dict(input_dict)
    expected = (("a", ()), ("b", "string"))
    assert result == expected


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@allure.story('Hashable Dict')
@allure.title('Test dictionary with different CustomUser objects')
def test_hashable_dict_with_different_users(llm):
    class MockUser:
        def __init__(self, id):
            self.id = id

        def __hash__(self):
            return hash(self.id)

        def __eq__(self, other):
            if isinstance(other, MockUser):
                return self.id == other.id
            return False

    user1 = MockUser(1)
    user2 = MockUser(2)

    input_dict1 = {"user": user1, "b": "string"}
    input_dict2 = {"user": user2, "b": "string"}

    result1 = llm._hashable_dict(input_dict1)
    result2 = llm._hashable_dict(input_dict2)

    # Check that the results are hashable
    assert isinstance(result1, tuple) and isinstance(result2, tuple)

    # Check that we can create sets from the results (which requires hashability)
    set1 = set(result1)
    set2 = set(result2)

    # Check that the sets are different
    assert set1 != set2

    # Check that the hashes are different
    assert hash(result1) != hash(result2)

    # Check that the user part is different
    user_tuple1 = next(item for item in result1 if item[0] == 'user')
    user_tuple2 = next(item for item in result2 if item[0] == 'user')
    assert user_tuple1 != user_tuple2

    # Check that other parts are the same
    assert next(item for item in result1 if item[0] == 'b') == next(item for item in result2 if item[0] == 'b')
    