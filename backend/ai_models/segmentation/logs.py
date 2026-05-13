import wandb

def log_and_save(epoch, total_epochs, 
                 train_loss, train_jaccard, train_dice, # Thêm track Jaccard/Dice cho Train
                 val_loss, val_jaccard, val_dice, 
                 val_accuracy, val_precision, val_recall, val_specificity, # Thêm các metrics mới
                 learning_rate, time_spent, 
                 log_file_path, is_best, is_wandb, is_txt):
    """
    Hàm tổng hợp để ghi log toàn diện vào terminal, wandb, file txt và lưu model.
    """
    # 1. Tạo chuỗi báo cáo (Chia làm 2 dòng cho dễ đọc trên terminal)
    report_line1 = (f"Epoch {epoch}/{total_epochs} | Time: {time_spent:.2f}s | LR: {learning_rate:.6f}\n")
    report_line2 = (f"  [Train] Loss: {train_loss:.4f} | IoU: {train_jaccard:.4f} | Dice: {train_dice:.4f}\n")
    report_line3 = (f"  [Val]   Loss: {val_loss:.4f} | IoU: {val_jaccard:.4f} | Dice: {val_dice:.4f} | "
                    f"Val Accuracy: {val_accuracy:.4f} | Val Precision: {val_precision:.4f} | Val Recall: {val_recall:.4f} | Val Specificity: {val_specificity:.4f}\"\n")
    
    full_report = report_line1 + report_line2 + report_line3
    
    # In ra terminal
    print(full_report)

    # 2. Log các chỉ số lên Weights & Biases
    if is_wandb:    
        wandb.log({
            "epoch": epoch,
            "epoch_time": time_spent,
            "learning_rate": learning_rate,
            # Train metrics
            "Train/Loss": train_loss,
            "Train/Jaccard_IoU": train_jaccard,
            "Train/Dice": train_dice,
            # Validation metrics
            "Validation/Loss": val_loss,
            "Validation/Jaccard_IoU": val_jaccard,
            "Validation/Dice": val_dice,
            "Validation/Accuracy": val_accuracy,
            "Validation/Precision": val_precision,
            "Validation/Recall": val_recall,
            "Validation/Specificity": val_specificity
        })

    if is_txt:
    # 3. Ghi vào file .txt và Lưu trọng số
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(full_report + "\n")
            if is_best:
                f.write("  >>> Model saved!\n")
            f.write("-" * 50 + "\n") 