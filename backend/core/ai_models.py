import os
import sys
import torch
from core.config import settings
from core.logger import logger
from ai_models.classification.predict_class import load_model_classification 
from ai_models.object_detection.predict_object import load_model_detection 
from ai_models.segmentation.predict_unet import load_unet_model 
from utils.embedding_utils import load_embedding_model 


class AIModelManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIModelManager, cls).__new__(cls)
            cls._instance.classification_model = None
            cls._instance.detection_model = None
            cls._instance.segmentation_model = None
            cls._instance.embedding_model = None
            cls._instance.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"AIModelManager initialized with device: {cls._instance.device}")
        return cls._instance

    def load_models(self):
        """Loads all AI models using the functions defined in the model-ai directory."""
        logger.info("Starting to load AI models using existing loaders...")
        
        # 1. Classification Model
        if settings.CLASSIFICATION_MODEL_PATH:
            try:
                self.classification_model = load_model_classification(
                    device=self.device, 
                    model_path=settings.CLASSIFICATION_MODEL_PATH
                )
                logger.info("Classification model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading Classification model: {e}")

        # 2. Detection Model
        if settings.DETECTION_MODEL_PATH:
            try:
                self.detection_model = load_model_detection(
                    device=self.device, 
                    model_path=settings.DETECTION_MODEL_PATH
                )
                logger.info("Detection model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading Detection model: {e}")

        # 3. Segmentation Model
        if settings.SEGMENTATION_MODEL_PATH:
            try:
                self.segmentation_model = load_unet_model(
                    device=self.device,
                    model_path=settings.SEGMENTATION_MODEL_PATH
                )
                logger.info("Segmentation model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading Segmentation model: {e}")

        # 4. Embedding Model (Dense & Sparse)
        try:
            from utils.embedding_utils import load_sparse_embedding_model
            self.embedding_model = load_embedding_model()
            logger.info("Dense Embedding model loaded successfully")
            
            self.sparse_embedding_model = load_sparse_embedding_model()
            logger.info("Sparse Embedding model (FastEmbed) loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Embedding models: {e}")

    @property
    def is_loaded(self):
        return all([self.classification_model, self.detection_model, self.segmentation_model, self.embedding_model])
