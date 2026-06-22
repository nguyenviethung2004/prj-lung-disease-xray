import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from tqdm import tqdm
from sklearn.metrics import confusion_matrix, classification_report

from data_processing import RawXrayDataModule
from classification_models import RSNADenseNet121


# =====================================================
# CONFIG
# =====================================================

IMAGE_SIZE = 380
BATCH_SIZE = 32
NUM_CLASSES = 3

# ---------- CROP ----------
CROP_DATA_DIR = r"D:\doan\dataset\rsna_classification_dataset\rsna_cropped_images"

CROP_SPLIT_FILE = r"D:\doan\backend\prj-lung-disease-xray\backend\ai_models\classification\model_best\3_class\crop\densse\data_split_by_name (4).pkl"

CROP_MODEL_PATH = r"D:\doan\backend\prj-lung-disease-xray\backend\ai_models\classification\model_best\3_class\crop\densse\densenet_380_epoch_11.pth"


# ---------- NO CROP ----------
NO_CROP_DATA_DIR = r"D:\doan\dataset\rsna_classification_dataset\data_raw"

NO_CROP_SPLIT_FILE = r"D:\doan\backend\prj-lung-disease-xray\backend\ai_models\classification\model_best\3_class\no_crop\densse\data_split_by_name (4).pkl"

NO_CROP_MODEL_PATH = r"D:\doan\backend\prj-lung-disease-xray\backend\ai_models\classification\model_best\3_class\no_crop\densse\densenet_380_no_crop_epoch_8.pth"


CLASS_NAMES = [
    "Normal",
    "COVID-19",
    "Pneumonia"
]


# =====================================================
# EVALUATE MODEL
# =====================================================

def evaluate_model(
    model_path,
    data_dir,
    split_file,
    device
):
    print("\n" + "=" * 60)
    print(f"MODEL: {model_path}")
    print("=" * 60)

    data_module = RawXrayDataModule(
        data_dir=data_dir,
        batch_size=BATCH_SIZE,
        image_size=IMAGE_SIZE,
        split_file=split_file
    )

    data_module.setup()

    test_loader = data_module.get_test_loader()

    model = RSNADenseNet121(
        num_classes=NUM_CLASSES
    )

    checkpoint = torch.load(
        model_path,
        map_location=device
    )

    if "model_state_dict" in checkpoint:
        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

    elif "state_dict" in checkpoint:
        model.load_state_dict(
            checkpoint["state_dict"]
        )

    else:
        model.load_state_dict(
            checkpoint
        )

    model.to(device)
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():

        for images, labels in tqdm(
            test_loader,
            desc="Predicting"
        ):
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)

            _, preds = torch.max(
                outputs,
                dim=1
            )

            all_preds.extend(
                preds.cpu().numpy()
            )

            all_labels.extend(
                labels.cpu().numpy()
            )

    print("\nClassification Report:\n")

    print(
        classification_report(
            all_labels,
            all_preds,
            target_names=CLASS_NAMES,
            digits=4
        )
    )

    cm = confusion_matrix(
        all_labels,
        all_preds
    )

    return cm


# =====================================================
# LABEL FOR HEATMAP
# =====================================================

def make_labels(cm):

    labels = np.empty(
        cm.shape,
        dtype=object
    )

    row_sum = cm.sum(
        axis=1,
        keepdims=True
    )

    percentages = (
        cm.astype(float)
        / row_sum
        * 100
    )

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):

            labels[i, j] = (
                f"{cm[i,j]}\n"
                f"{percentages[i,j]:.1f}%"
            )

    return labels


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(f"Using device: {device}")

    # ---------------------------------
    # Crop
    # ---------------------------------

    cm_crop = evaluate_model(
        model_path=CROP_MODEL_PATH,
        data_dir=CROP_DATA_DIR,
        split_file=CROP_SPLIT_FILE,
        device=device
    )

    # ---------------------------------
    # No Crop
    # ---------------------------------

    cm_no_crop = evaluate_model(
        model_path=NO_CROP_MODEL_PATH,
        data_dir=NO_CROP_DATA_DIR,
        split_file=NO_CROP_SPLIT_FILE,
        device=device
    )

    # ---------------------------------
    # Plot
    # ---------------------------------

    crop_labels = make_labels(
        cm_crop
    )

    nocrop_labels = make_labels(
        cm_no_crop
    )

    fig, axes = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(18, 7)
    )

    # ===============================
    # Crop
    # ===============================

    sns.heatmap(
        cm_crop,
        annot=crop_labels,
        fmt="",
        cmap="Blues",
        xticklabels=CLASS_NAMES,
        yticklabels=CLASS_NAMES,
        ax=axes[0]
    )

    axes[0].set_title(
        "DenseNet121 - Crop",
        fontsize=14,
        fontweight="bold"
    )

    axes[0].set_xlabel(
        "Predicted Label"
    )

    axes[0].set_ylabel(
        "True Label"
    )

    # ===============================
    # No Crop
    # ===============================

    sns.heatmap(
        cm_no_crop,
        annot=nocrop_labels,
        fmt="",
        cmap="Greens",
        xticklabels=CLASS_NAMES,
        yticklabels=CLASS_NAMES,
        ax=axes[1]
    )

    axes[1].set_title(
        "DenseNet121 - No Crop",
        fontsize=14,
        fontweight="bold"
    )

    axes[1].set_xlabel(
        "Predicted Label"
    )

    axes[1].set_ylabel(
        "True Label"
    )

    plt.suptitle(
        "Confusion Matrix Comparison",
        fontsize=18,
        fontweight="bold"
    )

    plt.tight_layout()

    plt.savefig(
        "compare_confusion_matrix.png",
        dpi=300,
        bbox_inches="tight"
    )

    print(
        "\nSaved: compare_confusion_matrix.png"
    )

    plt.show()