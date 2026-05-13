import os
import pydicom
import numpy as np
import cv2

def convert_dicom_to_png(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_list = os.listdir(input_dir)
    
    for filename in file_list:
        input_path = os.path.join(input_dir, filename)
        
        # Cắt bỏ đuôi cũ và đổi thành đuôi .png
        # Ví dụ: "001.dicom" -> base_name là "001" -> output là "001.png"
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}.png"
        output_path = os.path.join(output_dir, output_filename)

        try:
            # Đọc file DICOM
            dicom_data = pydicom.dcmread(input_path)
            
            if not hasattr(dicom_data, 'pixel_array'):
                continue

            # Xử lý ảnh
            pixel_array = dicom_data.pixel_array
            img_min = pixel_array.min()
            img_max = pixel_array.max()

            # Chuẩn hóa về 0-255
            if img_max > img_min:
                normalized_img = (pixel_array - img_min) / (img_max - img_min) * 255.0
            else:
                normalized_img = pixel_array

            final_img = np.uint8(normalized_img)

            # Lưu ảnh PNG
            cv2.imwrite(output_path, final_img)
            print(f"Đã chuyển: {filename} -> {output_filename}")

        except Exception as e:
            print(f"Lỗi ở file {filename}: {e}")

# Chạy thử
# if __name__ == "__main__":
#     THU_MUC_VAO = "D:\\doan\\backend\\prj-lung-disease-xray\\dataset\\rsna-pneumonia-detection-challenge\\stage_2_train_images"   # Thay bằng thư mục chứa ảnh 001.dicom của bạn
#     THU_MUC_RA = "D:\\doan\\backend\\prj-lung-disease-xray\\dataset\\rsna-pneumonia-detection-challenge\\rsna_pneumonia_png"     # Thư mục lưu ảnh 001.png

#     convert_dicom_to_png(THU_MUC_VAO, THU_MUC_RA)
