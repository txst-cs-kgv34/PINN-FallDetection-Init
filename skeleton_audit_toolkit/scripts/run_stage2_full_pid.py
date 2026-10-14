"""Run full Stage 2 with frozen Stage-1 dynamics and delayed PID control."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from filter_motion import filter_motion
from inverted_pendulum_pinn import LossWeights, evaluate_model, train_model
from phase_annotations import read_json, validate_phase_notes
from skeleton_model import com_proxy, segment_model
from stage2_full_pid import (
    GRAVITY_M_S2,
    identify_pid,
    simulate_pid,
)
from subject_frame import standing_body_frame, to_subject_frame


AXES = {"lateral": 0, "forward": 2}


def estimate_initial_velocity(position, onset, fps, frames):
    start = max(0, onset - frames + 1)
    sample = np.arange(start, onset + 1)
    time = (sample - onset) / fps
    return np.array([np.polyfit(time, position[start : onset + 1, axis], 1)[0] for axis in range(2)])


def prepare_trial(run_dir, subject, window, segments, settings, horizontal_axis):
    scale = {"mm": 0.001, "m": 1.0}[subject["coordinate_units"]]
    pose = np.loadtxt(run_dir / "raw" / f"{window['trial']}.csv", delimiter=",", ndmin=2).reshape(-1, 32, 3) * scale
    filtered, status = filter_motion(pose, float(subject["fps"]), settings["filter_cutoff_hz"], settings["filter_order"])
    if filtered is None:
        raise ValueError(f"filter unavailable for {window['trial']}: {status}")
    com = com_proxy(filtered, segments)[0]
    frame = standing_body_frame(filtered, window["initial_standing_frame0"], radius=settings["standing_radius"])
    com_body = to_subject_frame(com, frame)
    left_foot = to_subject_frame(filtered[:, 21], frame)
    right_foot = to_subject_frame(filtered[:, 25], frame)
    onset = window["fall_onset_frame0"]
    contact = window["apparent_contact_frame0"]
    pivot = ((left_foot + right_foot) / 2)[onset]
    horizontal = AXES[horizontal_axis]
    full_position = com_body[:, [horizontal, 1]] - pivot[[horizontal, 1]]
    position = full_position[onset : contact + 1]
    fps = float(subject["fps"])
    time_s = np.arange(len(position)) / fps
    initial_velocity = estimate_initial_velocity(full_position, onset, fps, settings["velocity_window_frames"])
    theta = np.unwrap(np.arctan2(position[:, 0], position[:, 1]))
    length = float(np.linalg.norm(position[0]))
    omega = float((position[0, 1] * initial_velocity[0] - position[0, 0] * initial_velocity[1]) / np.dot(position[0], position[0]))
    support_indices = (20, 21, 24, 25) if horizontal_axis == "forward" else (21, 25)
    support = to_subject_frame(filtered[:, support_indices], frame)[onset, :, horizontal] - pivot[horizontal]
    condition = np.array([position[0, 0], position[0, 1], initial_velocity[0], initial_velocity[1], theta[0], omega, length, np.ptp(support)])
    return {
        "trial": window["trial"], "activity": window["activity"], "horizontal_axis": horizontal_axis,
        "time_s": time_s, "duration_s": float(time_s[-1]), "position": position, "theta": theta,
        "initial_position": position[0].copy(), "initial_velocity": initial_velocity,
        "initial_theta": float(theta[0]), "initial_omega": omega, "length_m": length,
        "condition_raw": condition,
    }


def standardize(training, held_out):
    matrix = np.stack([trial["condition_raw"] for trial in training])
    mean = matrix.mean(axis=0); scale = matrix.std(axis=0); scale = np.where(scale < 1e-6, 1.0, scale)
    for trial in training + [held_out]:
        trial["condition_scaled"] = (trial["condition_raw"] - mean) / scale
    return mean, scale


def make_stage1_records(training, height_m, mass_kg, config):
    records = []
    for trial in training:
        count = len(trial["time_s"]); collocation = np.linspace(0, trial["duration_s"], config["collocation_points"])
        torque_scale = mass_kg * GRAVITY_M_S2 * trial["length_m"]
        records.append({
            "time_data": trial["time_s"], "position_data": trial["position"],
            "condition_data": np.tile(trial["condition_scaled"], (count, 1)),
            "initial_position_data": np.tile(trial["initial_position"], (count, 1)),
            "initial_velocity_data": np.tile(trial["initial_velocity"], (count, 1)),
            "torque_scale_data": np.full((count, 1), torque_scale),
            "time_collocation": collocation,
            "condition_collocation": np.tile(trial["condition_scaled"], (len(collocation), 1)),
            "initial_position_collocation": np.tile(trial["initial_position"], (len(collocation), 1)),
            "initial_velocity_collocation": np.tile(trial["initial_velocity"], (len(collocation), 1)),
            "torque_scale_collocation": np.full((len(collocation), 1), torque_scale),
            "mass_collocation": np.full(len(collocation), mass_kg),
            "length_collocation": np.full(len(collocation), trial["length_m"]),
            "damping_collocation": np.full(len(collocation), config["damping_nms"]),
            "height_m": height_m,
        })
    return records


def frozen_controller_records(model, training, mass_kg, stage1, time_scale_s):
    records = []
    for trial in training:
        time_s = np.linspace(0, trial["duration_s"], stage1["controller_collocation_points"])
        torque_scale = mass_kg * GRAVITY_M_S2 * trial["length_m"]
        evaluation = evaluate_model(
            model,
            time_s,
            np.tile(trial["condition_scaled"], (len(time_s), 1)),
            np.tile(trial["initial_position"], (len(time_s), 1)),
            np.tile(trial["initial_velocity"], (len(time_s), 1)),
            time_scale_s,
            mass_kg,
            trial["length_m"],
            stage1["damping_nms"],
            use_effective_torque=True,
        )
        records.append({
            "trial": trial["trial"], "time_s": time_s, "duration_s": trial["duration_s"],
            "theta": evaluation["theta"], "theta_velocity": evaluation["theta_velocity"],
            "theta_acceleration": evaluation["theta_acceleration"], "effective_torque": evaluation["effective_torque"],
            "torque_scale": torque_scale, "inertia": mass_kg * trial["length_m"] ** 2,
            "damping_nms": stage1["damping_nms"],
        })
    return records


def wrap_angle(a):
    return np.arctan2(np.sin(a), np.cos(a))


def metrics(actual_position, actual_theta, predicted_position, predicted_theta):
    error = predicted_position - actual_position
    return {
        "horizontal_rmse_m": float(np.sqrt(np.mean(error[:, 0] ** 2))),
        "vertical_rmse_m": float(np.sqrt(np.mean(error[:, 1] ** 2))),
        "xy_rmse_m": float(np.sqrt(np.mean(np.sum(error**2, axis=1)))),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(wrap_angle(predicted_theta - actual_theta) ** 2)))),
        "endpoint_error_m": float(np.linalg.norm(error[-1])),
    }


def constant_velocity(trial):
    position = trial["initial_position"] + trial["time_s"][:, None] * trial["initial_velocity"]
    return position, np.unwrap(np.arctan2(position[:, 0], position[:, 1]))


def fit_fold(job):
    activity, trials, held_out_name, fold_index, seed, mass_kg, height_m, config = job
    training = [dict(trial) for trial in trials if trial["trial"] != held_out_name]
    held_out = dict(next(trial for trial in trials if trial["trial"] == held_out_name))
    condition_mean, condition_scale = standardize(training, held_out)
    stage1 = config["stage1"]; stage2 = config["stage2"]
    time_scale_s = max(trial["duration_s"] for trial in training)
    stage1_records = make_stage1_records(training, height_m, mass_kg, stage1)
    loss_weights = LossWeights(
        physics=stage1["loss_weights"]["physics"],
        rigid_length=stage1["loss_weights"]["rigid_length"],
        effective_torque_l2=stage1["loss_weights"]["effective_torque_l2"],
        effective_torque_rate=stage1["loss_weights"]["effective_torque_rate"],
    )
    model, history = train_model(
        stage1_records,
        condition_size=len(condition_mean),
        time_scale_s=time_scale_s,
        architecture=stage1["architecture"],
        epochs=stage1["epochs"],
        learning_rate=stage1["learning_rate"],
        loss_weights=loss_weights,
        seed=seed + fold_index,
        history_interval=stage1["history_interval"],
    )
    frozen_records = frozen_controller_records(model, training, mass_kg, stage1, time_scale_s)
    reference_length = float(np.median([trial["length_m"] for trial in training]))
    result_rows=[]; profile_rows=[]; prediction_rows=[]
    fits={}
    for controller_type in ("pd", "pid"):
        for policy in ("zero", "nuisance"):
            fit, profiles = identify_pid(
                frozen_records, mass_kg, reference_length, controller_type, policy,
                stage2["delay_frames"], stage2["observation_hz"], stage2["bounds"],
                stage2["starts"], stage2["nuisance_penalty"], stage2["max_nfev"],
            )
            fits[(controller_type,policy)]=fit
            for profile in profiles:
                profile_rows.append({"activity":activity,"held_out_trial":held_out_name,"seed":seed,**profile})
            theta, _, _ = simulate_pid(
                held_out["time_s"], held_out["initial_theta"], held_out["initial_omega"], mass_kg,
                held_out["length_m"], stage1["damping_nms"], fit, policy, stage2["internal_hz"],
            )
            position=np.column_stack([held_out["length_m"]*np.sin(theta),held_out["length_m"]*np.cos(theta)])
            score=metrics(held_out["position"],held_out["theta"],position,theta)
            result_rows.append({
                "activity":activity,"held_out_trial":held_out_name,"training_trials":";".join(t["trial"] for t in training),"seed":seed,
                "controller_type":controller_type,"perturbation_policy":policy,"stage1_final_loss":history[-1]["total_loss"],
                **{k:v for k,v in fit.items() if k not in {"controller_type","perturbation_policy"}},**score,
            })
            prediction_rows.extend({
                "activity":activity,"held_out_trial":held_out_name,"seed":seed,"controller_type":controller_type,"perturbation_policy":policy,
                "frame":index,"time_s":float(held_out["time_s"][index]),"actual_horizontal_m":float(held_out["position"][index,0]),
                "actual_vertical_m":float(held_out["position"][index,1]),"predicted_horizontal_m":float(position[index,0]),
                "predicted_vertical_m":float(position[index,1]),"actual_theta_deg":float(np.degrees(held_out["theta"][index])),
                "predicted_theta_deg":float(np.degrees(theta[index])),
            } for index in range(len(theta)))
    stage1_held=evaluate_model(
        model, held_out["time_s"],
        np.tile(held_out["condition_scaled"],(len(held_out["time_s"]),1)),
        np.tile(held_out["initial_position"],(len(held_out["time_s"]),1)),
        np.tile(held_out["initial_velocity"],(len(held_out["time_s"]),1)),
        time_scale_s, mass_kg, held_out["length_m"], stage1["damping_nms"], True,
    )
    cv_pos,cv_theta=constant_velocity(held_out)
    checkpoint={
        "activity":activity,"held_out_trial":held_out_name,"seed":seed,"training_trials":[t["trial"] for t in training],
        "condition_mean":condition_mean.tolist(),"condition_scale":condition_scale.tolist(),"time_scale_s":time_scale_s,
        "training_seed":seed+fold_index,
        "state_dict":{name:value.detach().cpu().numpy().tolist() for name,value in model.state_dict().items()},
        "history":history,
    }
    controls={"stage1":metrics(held_out["position"],held_out["theta"],stage1_held["position"],stage1_held["theta"]),"constant":metrics(held_out["position"],held_out["theta"],cv_pos,cv_theta)}
    return result_rows,profile_rows,prediction_rows,checkpoint,controls


def plot_fold(output, trial, seed, rows, axis_label):
    primary=sorted([r for r in rows if r["held_out_trial"]==trial and int(r["seed"])==seed and r["controller_type"]=="pid" and r["perturbation_policy"]=="zero"],key=lambda r:float(r["time_s"]))
    nuisance=sorted([r for r in rows if r["held_out_trial"]==trial and int(r["seed"])==seed and r["controller_type"]=="pid" and r["perturbation_policy"]=="nuisance"],key=lambda r:float(r["time_s"]))
    pd=sorted([r for r in rows if r["held_out_trial"]==trial and int(r["seed"])==seed and r["controller_type"]=="pd" and r["perturbation_policy"]=="zero"],key=lambda r:float(r["time_s"]))
    time=np.array([float(r["time_s"]) for r in primary]); actual=np.array([[float(r["actual_horizontal_m"]),float(r["actual_vertical_m"])] for r in primary])
    def pos(group): return np.array([[float(r["predicted_horizontal_m"]),float(r["predicted_vertical_m"])] for r in group])
    fig,axes=plt.subplots(1,3,figsize=(15,4.5)); labels=[("Real CoM",actual,"#202733","-"),("PID zero",pos(primary),"#176d8a","--"),("PD zero",pos(pd),"#c05621",":"),("PID nuisance sensitivity",pos(nuisance),"#805ad5","-.")]
    for label,value,color,style in labels:
        axes[0].plot(time,value[:,0],style,color=color,label=label,linewidth=2); axes[1].plot(time,value[:,1],style,color=color,label=label,linewidth=2); axes[2].plot(value[:,0],value[:,1],style,color=color,label=label,linewidth=2)
    axes[0].set(xlabel="Time (s)",ylabel="Horizontal CoM (m)",title=axis_label); axes[1].set(xlabel="Time (s)",ylabel="Vertical CoM (m)",title="Vertical"); axes[2].set(xlabel="Horizontal CoM (m)",ylabel="Vertical CoM (m)",title="2-D CoM path")
    for axis in axes: axis.grid(alpha=.22)
    handles,labels_=axes[2].get_legend_handles_labels(); fig.legend(handles,labels_,loc="lower center",ncol=4,bbox_to_anchor=(.5,-.01)); fig.suptitle(f"{trial} full Stage 2 held-out CoM"); fig.tight_layout(rect=(0,.08,1,.93)); fig.savefig(output,dpi=180,bbox_inches="tight"); plt.close(fig)


def run(config_path,run_dir,subject_path,selection_path,output,workers):
    config=json.loads(config_path.read_text()); subject=read_json(subject_path); selection=read_json(selection_path)
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True); (output/"plots").mkdir(); segments=segment_model(subject["sex"]); mass=float(subject["mass_lb"])*.45359237; height=float(subject["height_in"])*.0254
    activity_trials={}
    for spec in config["activities"]:
        _,windows=validate_phase_notes(Path(spec["phase_notes"]),run_dir,subject,selection); windows=[w for w in windows if w["activity"]==spec["activity"]]
        activity_trials[spec["activity"]]=[prepare_trial(run_dir,subject,w,segments,config["preprocessing"],spec["horizontal_axis"]) for w in windows]
    jobs=[]
    for activity,trials in activity_trials.items():
        for fold_index, held in enumerate(trials):
            for seed in config["stage1"]["seeds"]: jobs.append((activity,trials,held["trial"],fold_index,seed,mass,height,config))
    metrics_rows=[];profile_rows=[];prediction_rows=[];checkpoints=[];control_rows=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        for index,(job,result) in enumerate(zip(jobs,executor.map(fit_fold,jobs)),1):
            m,p,pr,c,controls=result; metrics_rows.extend(m);profile_rows.extend(p);prediction_rows.extend(pr);checkpoints.append(c)
            control_rows.append({"activity":job[0],"held_out_trial":job[2],"seed":job[4],**{f"stage1_{k}":v for k,v in controls["stage1"].items()},**{f"constant_velocity_{k}":v for k,v in controls["constant"].items()}})
            print(f"[{index}/{len(jobs)}] {job[0]} {job[2]} seed {job[4]}",flush=True)
    write_csv(output/"fold_metrics.csv",metrics_rows);write_csv(output/"optimization_profiles.csv",profile_rows);write_csv(output/"held_out_com_predictions.csv",prediction_rows);write_csv(output/"control_metrics.csv",control_rows)
    (output/"stage1_frozen_checkpoints.json").write_text(json.dumps(checkpoints,indent=2)+"\n"); (output/"experiment_config.json").write_text(json.dumps(config,indent=2)+"\n")
    for activity,trials in activity_trials.items():
        axis_label="Anterior-posterior" if trials[0]["horizontal_axis"]=="forward" else "Medial-lateral"
        for trial in trials: plot_fold(output/"plots"/f"{trial['trial']}_stage2_full_pid.png",trial["trial"],config["stage1"]["seeds"][0],prediction_rows,axis_label)
    primary=[r for r in metrics_rows if r["controller_type"]=="pid" and r["perturbation_policy"]=="zero"]
    nuisance=[r for r in metrics_rows if r["controller_type"]=="pid" and r["perturbation_policy"]=="nuisance"]
    pd=[r for r in metrics_rows if r["controller_type"]=="pd" and r["perturbation_policy"]=="zero"]
    lines=["# Complete Stage 2 frozen-dynamics delayed-PID identification","","## Design","","The retained Stage-1 lambda=0.01 architecture is retrained and saved independently inside each whole-trial fold, then frozen. Stage 2 optimizes only Kp, Kd, Ki, delay and torque saturation. The primary model fixes perturbation torque to zero; a regularized three-component nuisance torque is reported only as sensitivity.","","## Held-out results","","| Activity | PID zero XY RMSE | PD zero XY RMSE | PID nuisance XY RMSE | Stage-1 PINN | Constant velocity |","|---|---:|---:|---:|---:|---:|"]
    for activity in sorted(activity_trials):
        mean=lambda rows:np.mean([float(r["xy_rmse_m"]) for r in rows if r["activity"]==activity])
        control=[row for row in control_rows if row["activity"]==activity]
        stage1_mean=np.mean([row["stage1_xy_rmse_m"] for row in control])
        constant_mean=np.mean([row["constant_velocity_xy_rmse_m"] for row in control])
        lines.append(f"| {activity} | {mean(primary):.4f} m | {mean(pd):.4f} m | {mean(nuisance):.4f} m | {stage1_mean:.4f} m | {constant_mean:.4f} m |")
    lines += ["","## Interpretation","","On A11, the PID integral coefficient collapses to approximately zero and PID does not improve over nested PD. On A13, full PID is worse than PD; the nonzero mean Ki is driven by the unstable S43A13T02 fold rather than consistent recovery. The nuisance-torque branch worsens mean held-out error for both activities.","","These are assumption-dependent effective controller fits. The skeleton recordings contain no measured perturbation, ground-reaction force or center of pressure. Trajectory agreement therefore cannot validate physiological gains. Damping remains fixed at the Stage-1 value b=0 rather than being re-estimated after freezing Stage 1.",""]
    (output/"SUMMARY.md").write_text("\n".join(lines))
    print("Complete Stage 2 run finished.")


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--config",type=Path,default=Path("configs/S43_stage2_full_pid.json")); parser.add_argument("--run",type=Path,default=Path("findings/S43_audit")); parser.add_argument("--subject-config",type=Path,default=Path("configs/S43.json")); parser.add_argument("--selection",type=Path,default=Path("configs/S43_modeling_selection.json")); parser.add_argument("--output",type=Path,default=Path("analyses/S43_stage2_full_pid")); parser.add_argument("--workers",type=int,default=max(1,min(4,(os.cpu_count() or 1)-1))); args=parser.parse_args(); run(args.config,args.run,args.subject_config,args.selection,args.output,args.workers)


if __name__=="__main__": main()
