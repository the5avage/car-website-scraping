# third party libraries
import torch
from transformers import AutoModel


def main():
    # 1. Grab the pretrained model (weights + config)
    model = AutoModel.from_pretrained("bert-base-uncased")

    # 2. Save only the weights (state_dict) as a pickle file
    torch.save(model.state_dict(), "car_matcher.pkl")
    print("✅ Saved bert-base-uncased weights to model.pkl")


if __name__ == "__main__":
    main()
