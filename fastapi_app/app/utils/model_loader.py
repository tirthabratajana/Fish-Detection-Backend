"""
Model loader utility for YOLO, EfficientNet (classification), and Disease Detection models
"""
import os
import json
import logging
from typing import Optional, Tuple
import tensorflow as tf
from ultralytics import YOLO


# 1. Turn off oneDNN custom operations
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# 2. Optional: Suppress other standard info logs (0=all logs, 1=no INFO, 2=no WARNING)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton class to load and manage AI models"""
    
    _instance = None
    _yolo_model: Optional[YOLO] = None
    _efficientnet_model: Optional[tf.keras.Model] = None
    _disease_model: Optional[tf.lite.Interpreter] = None
    _class_names: Optional[list] = None
    _models_loaded: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance
    
    @staticmethod
    def setup_models(
        yolo_model_path: str,
        efficientnet_model_path: str,
        disease_model_path: str,
        class_map_path: str
    ) -> Tuple[YOLO, tf.keras.Model, tf.lite.Interpreter, list]:
        """
        Load YOLO, EfficientNet, and Disease Detection models from disk
        
        Args:
            yolo_model_path: Path to best.pt YOLO model
            efficientnet_model_path: Path to efficientnet_fish.h5 model
            disease_model_path: Path to fish_model.tflite disease model
            class_map_path: Path to clf_class_names.json
            
        Returns:
            Tuple of (yolo_model, efficientnet_model, disease_model, class_names)
        """
        loader = ModelLoader()
        
        try:
            # Load YOLO model
            if not os.path.exists(yolo_model_path):
                raise FileNotFoundError(f"YOLO model not found: {yolo_model_path}")
            
            logger.info(f"Loading YOLO model from {yolo_model_path}...")
            loader._yolo_model = YOLO(yolo_model_path)
            logger.info("✅ YOLO model loaded successfully")
            
            # Load EfficientNet model
            if not os.path.exists(efficientnet_model_path):
                raise FileNotFoundError(f"EfficientNet model not found: {efficientnet_model_path}")
            
            logger.info(f"Loading EfficientNet model from {efficientnet_model_path}...")
            loader._efficientnet_model = tf.keras.models.load_model(efficientnet_model_path)
            logger.info("✅ EfficientNet model loaded successfully")
            
            # Load Disease Detection model (SavedModel format)
            if not os.path.exists(disease_model_path):
                logger.warning(f"Disease model not found: {disease_model_path}")
                loader._disease_model = None
            else:
                try:
                    logger.info(f"Loading Disease Detection model (SavedModel) from {disease_model_path}...")
                    loader._disease_model = tf.saved_model.load(disease_model_path)
                    logger.info("✅ Disease Detection model loaded successfully (SavedModel)")
                except Exception as e:
                    logger.warning(f"Failed to load disease model: {str(e)}")
                    logger.warning("API will continue without disease detection")
                    loader._disease_model = None
            
            # Load class names
            if not os.path.exists(class_map_path):
                raise FileNotFoundError(f"Class map not found: {class_map_path}")
            
            logger.info(f"Loading class names from {class_map_path}...")
            with open(class_map_path, 'r') as f:
                loader._class_names = json.load(f)
            logger.info(f"✅ Loaded {len(loader._class_names)} species: {loader._class_names}")
            
            loader._models_loaded = True
            return loader._yolo_model, loader._efficientnet_model, loader._disease_model, loader._class_names
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise
    
    @staticmethod
    def get_models() -> Tuple[YOLO, tf.keras.Model, tf.lite.Interpreter, list]:
        """Get loaded models"""
        loader = ModelLoader()
        if not loader._models_loaded:
            raise RuntimeError("Models not loaded. Call setup_models() first.")
        return loader._yolo_model, loader._efficientnet_model, loader._disease_model, loader._class_names
    
    @staticmethod
    def is_loaded() -> bool:
        """Check if models are loaded"""
        loader = ModelLoader()
        return loader._models_loaded
