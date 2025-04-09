from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging

logger = logging.getLogger(__name__)

class SpamDetector:
    def __init__(self, model_path: str):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            logger.info("Модель анти-спама успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise

    def predict(self, text: str) -> tuple[bool, list[float]]:
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1).tolist()[0]
                is_spam = torch.argmax(logits, dim=1).item() == 1
            return is_spam, probs
        except Exception as e:
            logger.error(f"Ошибка определения спама: {e}")
            return False, [0.5, 0.5]
