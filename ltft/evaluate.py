import sys, os
import gzip, pickle
from time import time, sleep
from tqdm import tqdm
import hydra
from omegaconf import DictConfig, open_dict, OmegaConf

import random
import numpy as np
import torch
import dgl
from einops import rearrange, reduce, repeat

from data import get_data_loaders
from util import seed_torch, TransitionBuffer, get_mdp_class
from algorithm import DetailedBalanceTransitionBuffer

import pathlib
from pathlib import Path

torch.backends.cudnn.benchmark = True


def get_alg_buffer(cfg, device):
    assert cfg.alg in ["db", "fl"]
    buffer = TransitionBuffer(cfg.tranbuff_size, cfg)
    alg = DetailedBalanceTransitionBuffer(cfg, device)
    return alg, buffer

def get_logr_scaler(cfg, process_ratio=1., reward_exp=None):
    if reward_exp is None:
        reward_exp = float(cfg.reward_exp)

    if cfg.anneal == "linear":
        process_ratio = max(0., min(1., process_ratio)) # from 0 to 1
        reward_exp = reward_exp * process_ratio +\
                     float(cfg.reward_exp_init) * (1 - process_ratio)
    elif cfg.anneal == "none":
        pass
    else:
        raise NotImplementedError

    # (R/T)^beta -> (log R - log T) * beta
    def logr_scaler(sol_size, gbatch=None):
        logr = sol_size
        return logr * reward_exp
    return logr_scaler

def refine_cfg(cfg):
    with open_dict(cfg):
        cfg.device = cfg.d
        cfg.work_directory = os.getcwd()

        if cfg.task in ["mis", "maxindset", "maxindependentset",]:
            cfg.task = "MaxIndependentSet"
            cfg.wandb_project_name = "MIS"
        elif cfg.task in ["mds", "mindomset", "mindominateset",]:
            cfg.task = "MinDominateSet"
            cfg.wandb_project_name = "MDS"
        elif cfg.task in ["mc", "maxclique",]:
            cfg.task = "MaxClique"
            cfg.wandb_project_name = "MaxClique"
        elif cfg.task in ["mcut", "maxcut",]:
            cfg.task = "MaxCut"
            cfg.wandb_project_name = "MaxCut"
        else:
            raise NotImplementedError

        # architecture
        assert cfg.arch in ["gin"]

        # log reward shape
        cfg.reward_exp = cfg.rexp
        cfg.reward_exp_init = cfg.rexpit
        if cfg.anneal in ["lin"]:
            cfg.anneal = "linear"

        # training
        cfg.batch_size = cfg.bs
        cfg.batch_size_interact = cfg.bsit
        cfg.leaf_coef = cfg.lc
        cfg.same_graph_across_batch = cfg.sameg

        # data
        cfg.test_batch_size = cfg.tbs
        if "rb" in cfg.input:
            cfg.data_type = cfg.input.upper()
        elif "ba" in cfg.input:
            cfg.data_type = cfg.input.upper()
        else:
            cfg.data_type = "rb"

    del cfg.d, cfg.rexp, cfg.rexpit, cfg.bs, cfg.bsit, cfg.lc, cfg.sameg, cfg.tbs
    return cfg

@torch.no_grad()
def rollout(gbatch, cfg, alg):
    env = get_mdp_class(cfg.task)(gbatch, cfg)
    state = env.state

    ##### sample traj
    reward_exp_eval = None
    traj_s, traj_r, traj_a, traj_d = [], [], [], []
    while not all(env.done):
        action = alg.sample(gbatch, state, env.done, rand_prob=cfg.randp, reward_exp=reward_exp_eval)

        traj_s.append(state)
        traj_r.append(env.get_log_reward())
        traj_a.append(action)
        traj_d.append(env.done)
        state = env.step(action)

    ##### save last state
    traj_s.append(state)
    traj_r.append(env.get_log_reward())
    traj_d.append(env.done)
    assert len(traj_s) == len(traj_a) + 1 == len(traj_r) == len(traj_d)

    traj_s = torch.stack(traj_s, dim=1) # (sum of #node per graph in batch, max_traj_len)
    traj_r = torch.stack(traj_r, dim=1) # (batch_size, max_traj_len)
    traj_a = torch.stack(traj_a, dim=1) # (batch_size, max_traj_len-1)
    """
    traj_a is tensor like 
    [ 4, 30, 86, 95, 96, 29, -1, -1],
    [47, 60, 41, 11, 55, 64, 80, -1],
    [26, 38, 13,  5,  9, -1, -1, -1]
    """
    traj_d = torch.stack(traj_d, dim=1) # (batch_size, max_traj_len)
    """
    traj_d is tensor like 
    [False, False, False, False, False, False,  True,  True,  True],
    [False, False, False, False, False, False, False,  True,  True],
    [False, False, False, False, False,  True,  True,  True,  True]
    """
    traj_len = 1 + torch.sum(~traj_d, dim=1) # (batch_size, )

    ##### graph, state, action, done, reward, trajectory length
    batch = gbatch.cpu(), traj_s.cpu(), traj_a.cpu(), traj_d.cpu(), traj_r.cpu(), traj_len.cpu()
    return batch, env.batch_metric(state)


@hydra.main(config_path="configs", config_name="main")
def main(cfg: DictConfig):
    cfg = refine_cfg(cfg)
    device = torch.device(f"cuda:{cfg.device:d}" if torch.cuda.is_available() and cfg.device >= 0 else "cpu")
    print(f"Device: {device}")
    alg, buffer = get_alg_buffer(cfg, device)
    seed_torch(cfg.seed)
    print(str(cfg))
    print(f"Work directory: {os.getcwd()}")

    # Prepare data loaders
    train_loader, test_loader = get_data_loaders(cfg)
    trainset_size = len(train_loader.dataset)
    print(f"Trainset size: {trainset_size}")
    alg_save_path = os.path.abspath("./alg.pt")
    alg_save_path_best = os.path.abspath("./alg_best.pt")
    train_data_used = 0
    train_step = 0
    result = {"set_size": {}, "logr_scaled": {}, "train_data_used": {}, "train_step": {}, }

    # Set result directory from config
    result_dir = Path(cfg.result_path)
    result_dir.mkdir(parents=True, exist_ok=True)

    # Load algorithm state
    alg_load_path = Path(__file__).parent / pathlib.Path(cfg.alg_load)
    alg.load(alg_load_path)

    @torch.no_grad()
    def evaluate(ep, train_step, train_data_used, logr_scaler, result_dir):
        """
        Evaluate the model, save .result files for each graph, rankings, and statistics.

        Args:
            ep: Current epoch.
            train_step: Current training step.
            train_data_used: Amount of training data used.
            logr_scaler: Log reward scaler function.
            result_dir: Path to the directory for saving .result files.
        """
        torch.cuda.empty_cache()
        num_repeat = 20
        mis_ls, mis_top20_ls = [], []
        logr_ls = []
        rankings_all = []  # To store all rankings as lists
        pbar = tqdm(enumerate(test_loader))
        pbar.set_description(f"Test Epoch {ep:2d} Data used {train_data_used:5d}")
        total_rank1_per = 0
        total_top5_per = 0
        total_top10_per = 0
        total_steps = 0

        result_dir = Path(result_dir)
        work_dir = Path(os.getcwd())  # Default working directory
        result_dir.mkdir(parents=True, exist_ok=True)

        for batch_idx, gbatch in pbar:
            gbatch = gbatch.to(device)
            gbatch_rep = dgl.batch([gbatch] * num_repeat)

            # Get original graph file paths from the dataset
            if hasattr(test_loader.dataset, "graph_paths"):
                graph_file_paths = test_loader.dataset.graph_paths[
                    batch_idx * gbatch.batch_size: (batch_idx + 1) * gbatch.batch_size
                ]
            else:
                graph_file_paths = [f"graph_{batch_idx}_{i}.graph" for i in range(gbatch.batch_size)]

            env = get_mdp_class(cfg.task)(gbatch_rep, cfg)
            state = env.state
            while not all(env.done):
                action = alg.sample(gbatch_rep, state, env.done, rand_prob=0.)
                state, rankings, ranking_stats = env.step_with_ranking(action)

                # Append rankings (list of lists)
                rankings_all.append(rankings)

                # Accumulate ranking statistics
                total_steps += 1
                total_rank1_per += ranking_stats["rank1"]
                total_top5_per += ranking_stats["top5%"]
                total_top10_per += ranking_stats["top10%"]

            logr_rep = logr_scaler(env.get_log_reward())
            logr_ls += logr_rep.tolist()

            # Generate .result files
            largest_independent_sets = env.output_result(state, num_repeat)
            for graph_idx, (independent_set_vector, graph_file_path) in enumerate(
                zip(largest_independent_sets, graph_file_paths)
            ):
                sanitized_file_name = Path(graph_file_path).stem  # Remove extensions
                file_path = result_dir / f"{sanitized_file_name}.result"
                with open(file_path, "w") as f:
                    f.write("\n".join(map(str, independent_set_vector)) + "\n")

            curr_mis_rep = torch.tensor(env.batch_metric(state))
            curr_mis_rep = rearrange(curr_mis_rep, "(rep b) -> b rep", rep=num_repeat).float()
            mis_ls += curr_mis_rep.mean(dim=1).tolist()
            mis_top20_ls += curr_mis_rep.max(dim=1)[0].tolist()
            pbar.set_postfix({"Metric": f"{np.mean(mis_ls):.2f}+-{np.std(mis_ls):.2f}"})

        total_rank1_per /= total_steps
        total_top5_per /= total_steps
        total_top10_per /= total_steps

        # Save rankings to file in the working directory
        rankings_file = work_dir / "rankings.out"
        with open(rankings_file, "w") as f:
            for ranking_list in rankings_all:
                f.write(" ".join(map(str, ranking_list)) + "\n")  # Print each list as a line

        # Save statistics to file in the working directory
        stats_file = work_dir / "stats.out"
        with open(stats_file, "w") as f:
            f.write(f"Rank1 Percentage: {total_rank1_per:.2f}%\n")
            f.write(f"Top 5% Percentage: {total_top5_per:.2f}%\n")
            f.write(f"Top 10% Percentage: {total_top10_per:.2f}%\n")

        print(f"Rankings saved to {rankings_file}")
        print(f"Statistics saved to {stats_file}")

        print(f"Total rank1: {total_rank1_per:.2f}%, Total top 5%: {total_top5_per:.2f}%, Total top 10%: {total_top10_per:.2f}%")
        print(f"Test Epoch {ep:2d} Data used {train_data_used:5d}: "
            f"Metric={np.mean(mis_ls):.2f}+-{np.std(mis_ls):.2f}, "
            f"top20={np.mean(mis_top20_ls):.2f}, "
            f"LogR scaled={np.mean(logr_ls):.2e}+-{np.std(logr_ls):.2e}")

        result["set_size"][ep] = np.mean(mis_ls)
        result["logr_scaled"][ep] = np.mean(logr_ls)
        result["train_step"][ep] = train_step
        result["train_data_used"][ep] = train_data_used
        pickle.dump(result, gzip.open("./result.json", 'wb'))



    # Main evaluation loop
    logr_scaler = get_logr_scaler(cfg)
    evaluate(cfg.epochs, train_step, train_data_used, logr_scaler, result_dir)


if __name__ == "__main__":
    main()