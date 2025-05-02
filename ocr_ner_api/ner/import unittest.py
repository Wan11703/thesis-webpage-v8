import unittest
from unittest.mock import patch, MagicMock
from ner.app import extract_drug_names

# filepath: c:\Users\Mark\OneDrive\Desktop\thesis-webpage\ner\test_app.py

class TestExtractDrugNames(unittest.TestCase):
    @patch("ner.app.tokenizer")
    @patch("ner.app.model")
    def test_extract_drug_names_with_drugs(self, mock_model, mock_tokenizer):
        # Mock tokenizer output
        mock_tokenizer.return_value = {
            "input_ids": [[101, 1234, 5678, 102]],
            "attention_mask": [[1, 1, 1, 1]]
        }
        mock_tokenizer.convert_ids_to_tokens.return_value = ["[CLS]", "aspirin", "[SEP]"]

        # Mock model output
        mock_model.return_value.logits = torch.tensor([[[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

        # Mock id2label mapping
        mock_model.config.id2label = {0: "O", 1: "B-DRUG", 2: "I-DRUG"}

        # Call the function
        result = extract_drug_names("aspirin is a drug")

        # Assert the result
        self.assertEqual(result, ["aspirin"])

    @patch("ner.app.tokenizer")
    @patch("ner.app.model")
    def test_extract_drug_names_without_drugs(self, mock_model, mock_tokenizer):
        # Mock tokenizer output
        mock_tokenizer.return_value = {
            "input_ids": [[101, 1234, 5678, 102]],
            "attention_mask": [[1, 1, 1, 1]]
        }
        mock_tokenizer.convert_ids_to_tokens.return_value = ["[CLS]", "hello", "[SEP]"]

        # Mock model output
        mock_model.return_value.logits = torch.tensor([[[0, 1, 2], [0, 1, 2], [0, 1, 2]]])

        # Mock id2label mapping
        mock_model.config.id2label = {0: "O", 1: "B-DRUG", 2: "I-DRUG"}

        # Call the function
        result = extract_drug_names("hello world")

        # Assert the result
        self.assertEqual(result, [])

    @patch("ner.app.tokenizer")
    @patch("ner.app.model")
    def test_extract_drug_names_empty_input(self, mock_model, mock_tokenizer):
        # Mock tokenizer output
        mock_tokenizer.return_value = {
            "input_ids": [[101, 102]],
            "attention_mask": [[1, 1]]
        }
        mock_tokenizer.convert_ids_to_tokens.return_value = ["[CLS]", "[SEP]"]

        # Mock model output
        mock_model.return_value.logits = torch.tensor([[[0, 1], [0, 1]]])

        # Mock id2label mapping
        mock_model.config.id2label = {0: "O", 1: "B-DRUG", 2: "I-DRUG"}

        # Call the function
        result = extract_drug_names("")

        # Assert the result
        self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()