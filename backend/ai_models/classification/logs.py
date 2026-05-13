import wandb

def log_and_save(epoch, total_epochs, 
                 train_loss, train_acc, train_precision, train_recall, train_f1, train_specificity,
                 val_loss, val_acc, val_precision, val_recall, val_f1, val_specificity,
                 learning_rate, time_spent, 
                 log_file_path, is_best, is_wandb, is_txt):
    """
    Logging cho bài toán Classification
    """

    # 1. Report
    report_line1 = (f"Epoch {epoch}/{total_epochs} | Time: {time_spent:.2f}s | LR: {learning_rate:.6f}\n")
    
    report_line2 = (
        f"  [Train] Loss: {train_loss:.4f} | Acc: {train_acc:.4f} | "
        f"Precision: {train_precision:.4f} | Recall: {train_recall:.4f} | F1: {train_f1:.4f} | Specificity: {train_specificity:.4f}\n"
    )
    
    report_line3 = (
        f"  [Val]   Loss: {val_loss:.4f} | Acc: {val_acc:.4f} | "
        f"Precision: {val_precision:.4f} | Recall: {val_recall:.4f} | F1: {val_f1:.4f} | Specificity: {val_specificity:.4f}\n"
    )

    full_report = report_line1 + report_line2 + report_line3

    # In terminal
    print(full_report)

    # 2. WandB
    if is_wandb:
        wandb.log({
            "epoch": epoch,
            "epoch_time": time_spent,
            "learning_rate": learning_rate,

            # Train
            "Train/Loss": train_loss,
            "Train/Accuracy": train_acc,
            "Train/Precision": train_precision,
            "Train/Recall": train_recall,
            "Train/F1": train_f1,
            "Train/Specificity": train_specificity,
            # Validation
            "Validation/Loss": val_loss,
            "Validation/Accuracy": val_acc,
            "Validation/Precision": val_precision,
            "Validation/Recall": val_recall,
            "Validation/F1": val_f1,
            "Validation/Specificity": val_specificity,
        })

    # 3. TXT
    if is_txt:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(full_report + "\n")
            if is_best:
                f.write("  >>> Model saved!\n")
            f.write("-" * 50 + "\n")