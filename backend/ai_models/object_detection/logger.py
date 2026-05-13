# logger.py
import wandb

class WandbLogger:
    def __init__(self, project_name, run_name, config, disable=False):
        self.disable = disable
        if not self.disable:
            wandb.init(project=project_name, name=run_name, config=config)

    def log_train_step(self, total_loss, cls_loss, box_loss):
        """Log Loss theo từng bước (batch)"""
        if not self.disable:
            wandb.log({
                "Train/Total_Loss": total_loss,
                "Train/Cls_Loss": cls_loss,
                "Train/Box_Loss": box_loss
            })

    def log_val_metrics(self, epoch, map_50, map_75, lr):
        """Log Metrics sau khi kết thúc 1 Epoch"""
        if not self.disable:
            wandb.log({
                "Epoch": epoch,
                "Val/mAP_50": map_50,
                "Val/mAP_75": map_75,
                "Learning_Rate": lr
            })

    def finish(self):
        if not self.disable:
            wandb.finish()