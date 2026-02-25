import unittest
from unittest.mock import patch
from src.agent import answer_question

class TestAgent(unittest.TestCase):

    @patch('src.agent.requests.get')
    def test_answer_question_success(self, mock_get):
        # Mock the API response for a successful search
        mock_response_search = {
            "query": {
                "search": [
                    {"title": "Test Title"}
                ]
            }
        }
        # Mock the API response for a successful summary fetch
        mock_response_summary = {
            "query": {
                "pages": {
                    "123": {
                        "extract": "This is a test summary."
                    }
                }
            }
        }
        
        # Configure the mock to return different values on subsequent calls
        mock_get.side_effect = [
            unittest.mock.Mock(status_code=200, json=lambda: mock_response_search),
            unittest.mock.Mock(status_code=200, json=lambda: mock_response_summary)
        ]

        question = "What is a test?"
        expected_answer = "This is a test summary."
        self.assertEqual(answer_question(question), expected_answer)

    @patch('src.agent.requests.get')
    def test_answer_question_no_results(self, mock_get):
        # Mock the API response for a search with no results
        mock_response = {
            "query": {
                "search": []
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        question = "Non-existent topic"
        expected_answer = "I couldn't find any information on that topic."
        self.assertEqual(answer_question(question), expected_answer)

if __name__ == '__main__':
    unittest.main()
