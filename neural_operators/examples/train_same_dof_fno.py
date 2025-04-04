"""
In this example I fix all the hyperparameters for the FNO model and train it.
"""

import os
import sys

import torch

sys.path.append("..")

from datasets import NO_load_data_model
from FNO.FNO import FNO
from FNO.FNO_utilities import (
    FNO_initialize_hyperparameters,
    compute_modes,
    count_params_fno,
)
from loss_fun import loss_selector
from train import train_fixed_model
from utilities import get_plot_function
from wrappers.wrap_model import wrap_model_builder


def train_same_dofs_fno(which_example: str, loss_fn_str: str, maximum: int):

    # Select available device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Compute the total number of default parameters
    hyperparams_train, hyperparams_arc = FNO_initialize_hyperparameters(
        which_example, "default"
    )
    total_default_params = count_params_fno(
        {
            **hyperparams_train,
            **hyperparams_arc,
        },
        accurate=False,
    )
    # total_default_params = 500000

    # Load true hyper-parameters
    hyperparams_train, hyperparams_arc = FNO_initialize_hyperparameters(
        which_example, "best_samedofs"
    )
    default_hyper_params = {
        **hyperparams_train,
        **hyperparams_arc,
    }

    print(
        "The number of modes is:",
        compute_modes(total_default_params, maximum, default_hyper_params),
    )

    # Define the model builders
    model_builder = lambda config: FNO(
        config["problem_dim"],
        config["in_dim"],
        config["width"],
        config["out_dim"],
        config["n_layers"],
        compute_modes(total_default_params, maximum, config),
        config["fun_act"],
        config["weights_norm"],
        config["fno_arc"],
        config["RNN"],
        config["fft_norm"],
        config["padding"],
        device,
        config["retrain"],
    )
    # Wrap the model builder
    model_builder = wrap_model_builder(model_builder, which_example)

    # Define the dataset builder
    dataset_builder = lambda config: NO_load_data_model(
        which_example=which_example,
        no_architecture={
            "FourierF": config["FourierF"],
            "retrain": config["retrain"],
        },
        batch_size=config["batch_size"],
        training_samples=config["training_samples"],
    )

    # Define the loss function
    loss_fn = loss_selector(
        loss_fn_str=loss_fn_str,
        problem_dim=default_hyper_params["problem_dim"],
        beta=default_hyper_params["beta"],
    )

    experiment_name = f"FNO/{which_example}/loss_{loss_fn_str}_mode_best_samedofs"

    # Create the right folder if it doesn't exist
    folder = f"../tests/{experiment_name}"
    if not os.path.isdir(folder):
        print("Generated new folder")
        os.makedirs(folder, exist_ok=True)

    # Save the norm information
    with open(folder + "/norm_info.txt", "w") as f:
        f.write("Norm used during the training:\n")
        f.write(f"{loss_fn_str}\n")

    # Call the library function to tune the hyperparameters
    train_fixed_model(
        default_hyper_params,
        model_builder,
        dataset_builder,
        loss_fn,
        experiment_name,
        get_plot_function(which_example, "input"),
        get_plot_function(which_example, "output"),
    )


if __name__ == "__main__":
    train_same_dofs_fno("poisson", "L2", 33)
