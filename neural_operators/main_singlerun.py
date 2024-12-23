"""
This is the main file for training the Neural Operator with the FNO architecture for different examples.

"which_example" can be one of the following options:
    poisson             : Poisson equation 
    wave_0_5            : Wave equation 
    cont_tran           : Smooth Transport 
    disc_tran           : Discontinuous Transport
    allen               : Allen-Cahn equation # training_sample = 512
    shear_layer         : Navier-Stokes equations # training_sample = 512
    airfoil             : Compressible Euler equations 
    darcy               : Darcy equation

    burgers_zongyi      : Burgers equation
    darcy_zongyi        : Darcy equation
    navier_stokes_zongyi: Navier-Stokes equations

    fhn                 : FitzHugh-Nagumo equations in [0, 100]
    fhn_long            : FitzHugh-Nagumo equations in [0, 200]
    hh                  : Hodgkin-Huxley equations

    crosstruss          : Cross-shaped truss structure

"exp_norm" can be one of the following options:
    L1 : L^1 relative norm
    L2 : L^2 relative norm
    H1 : H^1 relative norm
    L1_smooth : L^1 smooth loss (Mishra)
    MSE : L^2 smooth loss (Mishra)
"""

import torch
from tensorboardX import SummaryWriter
import os
import json
from tqdm import tqdm
import argparse

from Loss_fun import LprelLoss, H1relLoss_1D, H1relLoss
from train_fun import train_fun, test_fun
from utilities import count_params, plot_data

# FNO imports
from FNO.FNO_arc import FNO_1D, FNO_2D
from FNO.FNO_utilities import FNO_initialize_hyperparameters, FNO_load_data_model

# CNO imports
from CNO.CNO_1d import CNO1d
from CNO.CNO_2d import CNO2d
from CNO.CNO_utilities import CNO_load_data_model, CNO_initialize_hyperparameters

#########################################
# default values
#########################################
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device: ", device)
# torch.set_default_dtype(torch.float32) # default tensor dtype


#########################################
# Choose the example to run
#########################################
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a specific example with the desired model and training configuration."
    )

    parser.add_argument(
        "example",
        type=str,
        choices=[
            "poisson",
            "wave_0_5",
            "cont_tran",
            "disc_tran",
            "allen",
            "shear_layer",
            "airfoil",
            "darcy",
            "burgers_zongyi",
            "darcy_zongyi",
            "fhn",
            "fhn_long",
            "hh",
            "crosstruss",
        ],
        help="Select the example to run.",
    )
    parser.add_argument(
        "architecture",
        type=str,
        choices=["fno", "cno"],
        help="Select the architecture to use.",
    )
    parser.add_argument(
        "loss_function",
        type=str,
        choices=["l1", "l2", "h1", "l1_smooth"],
        help="Select the relative loss function to use during the training process.",
    )
    parser.add_argument(
        "mode",
        type=str,
        choices=["best", "default"],
        help="Select the hyper-params to use for define the architecture and the training, we have implemented the 'best' and 'default' options.",
    )
    parser.add_argument(
        "--in_dist",
        type=bool,
        default=True,
        help="For the datasets that are supported you can select if the test set is in-distribution or out-of-distribution.",
    )

    args = parser.parse_args()

    return {
        "example": args.example.lower(),
        "architecture": args.architecture.upper(),
        "loss_function": args.loss_function.upper(),
        "mode": args.mode.lower(),
        "in_dist": args.in_dist,
    }


config = parse_arguments()
which_example = config["example"]
arc = config["architecture"]
exp_norm = config["loss_function"]
mode_str = config["mode"]
in_dist = config["in_dist"]

#########################################
# parameters for save the model
#########################################
folder = f"./{arc}/TrainedModels/{which_example}/exp_{arc}_test_{exp_norm}_{mode_str}_hyperparams"
name_model = f"./{arc}/TrainedModels/{which_example}/model_{arc}_test_{exp_norm}_{mode_str}_hyperparams"

writer = SummaryWriter(log_dir=folder)  # tensorboard

if not os.path.isdir(folder):
    # create the right folder if it doesn't exist
    print("Generated new folder")
    os.mkdir(folder)

#########################################
# Parameters for plots and tensorboard
#########################################
ep_step = 1  #! default is 50
n_idx = 4  # number of random test that we plot
plotting = False

#########################################
# Hyperparameters
#########################################
match arc:
    case "FNO":
        hyperparams_train, hyperparams_arc = FNO_initialize_hyperparameters(
            which_example, mode=mode_str
        )
    case "CNO":
        hyperparams_train, hyperparams_arc = CNO_initialize_hyperparameters(
            which_example, mode=mode_str
        )
    case _:
        raise ValueError("This architecture is not allowed")

# choose the Loss function
Norm_dict = {"L1": 0, "L2": 1, "H1": 2, "L1_SMOOTH": 3, "MSE": 4}
hyperparams_train["exp"] = Norm_dict[exp_norm]

# Training hyperparameters
learning_rate = hyperparams_train["learning_rate"]
weight_decay = hyperparams_train["weight_decay"]
scheduler_step = hyperparams_train["scheduler_step"]
scheduler_gamma = hyperparams_train["scheduler_gamma"]
epochs = hyperparams_train["epochs"]
batch_size = hyperparams_train["batch_size"]
p = hyperparams_train["exp"]
beta = hyperparams_train["beta"]
training_samples = hyperparams_train["training_samples"]
test_samples = hyperparams_train["test_samples"]
val_samples = hyperparams_train["val_samples"]

match arc:
    case "FNO":
        # fno architecture hyperparameters
        d_a = hyperparams_arc["d_a"]
        d_v = hyperparams_arc["width"]
        d_u = hyperparams_arc["d_u"]
        L = hyperparams_arc["n_layers"]
        modes = hyperparams_arc["modes"]
        fun_act = hyperparams_arc["fun_act"]
        weights_norm = hyperparams_arc["weights_norm"]
        fno_arc = hyperparams_arc["arc"]
        RNN = hyperparams_arc["RNN"]
        FFTnorm = hyperparams_arc["fft_norm"]
        padding = hyperparams_arc["padding"]
        retrain = hyperparams_arc["retrain"]
        FourierF = hyperparams_arc["FourierF"]
        problem_dim = hyperparams_arc["problem_dim"]

    case "CNO":
        # cno architecture hyperparameters
        in_dim = hyperparams_arc["in_dim"]
        out_dim = hyperparams_arc["out_dim"]
        size = hyperparams_arc["in_size"]
        n_layers = hyperparams_arc["N_layers"]
        chan_mul = hyperparams_arc["channel_multiplier"]
        n_res_neck = hyperparams_arc["N_res_neck"]
        n_res = hyperparams_arc["N_res"]
        kernel_size = hyperparams_arc["kernel_size"]
        bn = hyperparams_arc["bn"]
        retrain = hyperparams_arc["retrain"]
        problem_dim = hyperparams_arc["problem_dim"]

    case _:
        raise ValueError("This architecture is not allowed")

#########################################
# Data and model loader, depending on the example chosen
#########################################
match arc:
    case "FNO":
        example = FNO_load_data_model(
            which_example,
            hyperparams_arc,
            device,
            batch_size,
            training_samples,
            in_dist,
        )
    case "CNO":
        example = CNO_load_data_model(
            which_example,
            hyperparams_arc,
            device,
            batch_size,
            training_samples,
            in_dist,
        )

train_loader = example.train_loader
val_loader = example.val_loader

#########################################
# save hyper-parameter in txt and json files
#########################################
with open(folder + "/norm_info.txt", "w") as f:
    f.write("Norm used during the training:\n")
    f.write(f"{exp_norm}\n")

with open(folder + "/hyperparams_train.json", "w") as f:
    json.dump(hyperparams_train, f, indent=4)

with open(folder + "/hyperparams_arc.json", "w") as f:
    json.dump(hyperparams_arc, f, indent=4)

#########################################
# load the model
#########################################
match arc:
    case "FNO":
        if problem_dim == 1:
            model = FNO_1D(
                d_a,
                d_v,
                d_u,
                L,
                modes,
                fun_act,
                weights_norm,
                fno_arc,
                RNN,
                FFTnorm,
                padding,
                device,
                retrain,
            )
        elif problem_dim == 2:
            model = FNO_2D(
                d_a,
                d_v,
                d_u,
                L,
                modes,
                modes,
                fun_act,
                weights_norm,
                fno_arc,
                RNN,
                FFTnorm,
                padding,
                device,
                retrain,
            )
    case "CNO":
        if problem_dim == 1:
            model = CNO1d(
                in_dim,
                out_dim,
                size,
                n_layers,
                n_res,
                n_res_neck,
                chan_mul,
                kernel_size,
                bn,
                device,
            )
        elif problem_dim == 2:
            model = CNO2d(
                in_dim,
                out_dim,
                size,
                n_layers,
                n_res,
                n_res_neck,
                chan_mul,
                kernel_size,
                bn,
                device,
            )

# count and print the total number of parameters
par_tot = count_params(model)
print("Total number of parameters is: ", par_tot)
writer.add_text("Parameters", "total number of parameters is" + str(par_tot), 0)

#########################################
# Training
#########################################
# optimizer and scheduler
optimizer = torch.optim.AdamW(
    model.parameters(), lr=learning_rate, weight_decay=weight_decay
)

scheduler = torch.optim.lr_scheduler.StepLR(
    optimizer, step_size=scheduler_step, gamma=scheduler_gamma
)

# Loss function
match p:
    case 0:
        loss = LprelLoss(1, False)  # L^1 relative norm
    case 1:
        loss = LprelLoss(2, False)  # L^2 relative norm
    case 2:
        if problem_dim == 1:
            loss = H1relLoss_1D(beta, False, 1.0)
        elif problem_dim == 2:
            loss = H1relLoss(beta, False, 1.0)  # H^1 relative norm
    case 3:
        loss = torch.nn.SmoothL1Loss()  # L^1 smooth loss (Mishra)
    case 4:
        loss = torch.nn.MSELoss()  # L^2 smooth loss (Mishra)
    case _:
        raise ValueError("This value of p is not allowed")


#### Training process
for epoch in range(epochs):
    with tqdm(
        desc=f"Epoch {epoch}", bar_format="{desc}: [{elapsed_s:.2f}{postfix}]"
    ) as tepoch:

        # train the model for one epoch
        if epoch == 0:  # extract the test data
            esempio_test, soluzione_test = train_fun(
                model,
                train_loader,
                optimizer,
                scheduler,
                loss,
                p,
                device,
                which_example,
                tepoch,
                n_idx,
            )
        else:
            train_fun(
                model,
                train_loader,
                optimizer,
                scheduler,
                loss,
                p,
                device,
                which_example,
                tepoch,
            )

        # test the model for one epoch
        (
            test_relative_l1,
            test_relative_l2,
            test_relative_semih1,
            test_relative_h1,
            train_loss,
        ) = test_fun(
            model,
            val_loader,
            train_loader,
            loss,
            exp_norm,
            val_samples,
            training_samples,
            device,
            which_example,
            tepoch,
            statistic=True,
        )

        # save the results on tensorboard
        writer.add_scalars(
            f"{arc}_{problem_dim}D_" + which_example,
            {
                "Train loss " + exp_norm: train_loss,
                "Test rel. L^1 error": test_relative_l1,
                "Test rel. L^2 error": test_relative_l2,
                "Test rel. semi-H^1 error": test_relative_semih1,
                "Test rel. H^1 error": test_relative_h1,
            },
            epoch,
        )

        with open(folder + "/errors.txt", "w") as file:
            file.write("Training loss " + exp_norm + ": " + str(train_loss) + "\n")
            file.write("Test relative L^1 error: " + str(test_relative_l1) + "\n")
            file.write("Test relative L^2 error: " + str(test_relative_l2) + "\n")
            file.write(
                "Test relative semi-H^1 error: " + str(test_relative_semih1) + "\n"
            )
            file.write("Test relative H^1 error: " + str(test_relative_h1) + "\n")
            file.write("Current Epoch: " + str(epoch) + "\n")
            file.write("Params: " + str(par_tot) + "\n")

        # plot data during the training and save on tensorboard
        if epoch == 0:
            # plot the input data
            plot_data(
                example,
                esempio_test,
                [],
                "Input function",
                epoch,
                writer,
                which_example,
                problem_dim,
                plotting,
            )

            # plot the exact solution
            plot_data(
                example,
                soluzione_test,
                [],
                "Exact solution",
                epoch,
                writer,
                which_example,
                problem_dim,
                plotting,
            )

        # Approximate solution with NO
        if epoch % ep_step == 0:
            with torch.no_grad():  # no grad for efficiency
                out_test = model(esempio_test.to(device))
                out_test = out_test.cpu()

                # post-processing for the output
                if which_example == "airfoil":
                    out_test[esempio_test == 1] = 1
                elif which_example == "crosstruss":
                    for i in range(out_test.shape[-1]):
                        out_test[:, :, :, [i]] = out_test[:, :, :, [i]] * esempio_test

            # plot the approximate solution
            plot_data(
                example,
                out_test,
                [],
                f"Approximate solution with {arc}",
                epoch,
                writer,
                which_example,
                problem_dim,
                plotting,
            )

            # Module of the difference
            diff = torch.abs(out_test - soluzione_test)
            plot_data(
                example,
                diff,
                [],
                "Module of the error",
                epoch,
                writer,
                which_example,
                problem_dim,
                plotting,
            )

writer.flush()  # for saving final data
writer.close()  # close the tensorboard writer

torch.save(model, name_model)
