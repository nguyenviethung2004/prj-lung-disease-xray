// This file acts as a simple in-memory database for our mock API.
// In development, Next.js might clear this on fast refresh, but it's sufficient for simulation.

export type TrainingRecord = {
  id: string;
  model: string;
  dataset: string;
  start: string;
  end: string;
  status: "Success" | "Failed" | "Running";
  accuracy: string;
  loss: string;
  map?: string;
  config: any;
  logs: string;
  progress?: number; // 0 to 100
};

export const store = {
  data: [
    {
      id: "TRN-001",
      model: "ResNet-50",
      dataset: "Chest X-Ray v2",
      start: "2026-03-15 08:00",
      end: "2026-03-15 14:30",
      status: "Success",
      accuracy: "94.5%",
      loss: "0.12",
      map: "89.4%",
      config: { learning_rate: 0.001, batch_size: 32, epochs: 100, optimizer: "Adam", image_size: 256 },
      logs: "Epoch 1/100\n- loss: 0.854 - accuracy: 0.652\n...\nTraining completed successfully.\nModel saved.",
    },
    {
      id: "TRN-002",
      model: "YOLOv8-Med",
      dataset: "MRI Scans",
      start: "2026-03-16 09:15",
      end: "2026-03-16 11:20",
      status: "Success",
      accuracy: "89.2%",
      loss: "0.24",
      config: { learning_rate: 0.01, batch_size: 16, epochs: 50, optimizer: "SGD", image_size: 512 },
      logs: "Training finished.",
    },
    {
      id: "TRN-003",
      model: "EfficientNet",
      dataset: "Skin Lesions",
      start: new Date().toISOString().replace('T', ' ').substring(0, 16),
      end: "-",
      status: "Running",
      accuracy: "-",
      loss: "-",
      progress: 45,
      config: { learning_rate: 0.0005, batch_size: 64, epochs: 200, optimizer: "AdamW", image_size: 224 },
      logs: "Epoch 1/200\n- loss: 1.201 - accuracy: 0.450\nEpoch 45/200\n- loss: 0.601 - accuracy: 0.780",
    }
  ] as TrainingRecord[],

  simulateProgress() {
    this.data.forEach(record => {
      if (record.status === "Running") {
        if (!record.progress) record.progress = 0;
        record.progress += Math.floor(Math.random() * 15) + 5; // advance 5-20%
        
        let currentEpoch = Math.floor((record.progress / 100) * record.config.epochs);
        let currentAcc = (0.5 + (record.progress / 100) * 0.45).toFixed(3);
        let currentLoss = (1.5 - (record.progress / 100) * 1.3).toFixed(3);

        record.logs += `\nEpoch ${currentEpoch}/${record.config.epochs}\n- loss: ${currentLoss} - accuracy: ${currentAcc}`;

        if (record.progress >= 100) {
          record.progress = 100;
          record.status = "Success";
          record.end = new Date().toISOString().replace('T', ' ').substring(0, 16);
          record.accuracy = (parseFloat(currentAcc) * 100).toFixed(1) + "%";
          record.loss = currentLoss;
          record.logs += "\nTraining completed successfully.\nModel saved.";
        }
      }
    });
  }
};
