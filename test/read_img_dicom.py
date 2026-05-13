import pandas as pd

# nếu cách nhau bằng khoảng trắng
df = pd.read_csv(r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\2_crop\cropped_labels_target1.txt", sep=",", header=0)

df.to_csv(r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\label_crop.csv", index=False)