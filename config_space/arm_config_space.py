import numpy as np
import matplotlib.pyplot as plt
import polygon_tools as poly
import robot_tools
from matplotlib.patches import Polygon as PlotPolygon
from matplotlib.collections import PatchCollection
import matplotlib.animation as animation
import matplotlib.cm as cm
import argparse

""" 

Plot the config space from Introduction to Autonomous Mobile Robots Fig 6.1 

Requires: numpy, matplotlib, argparse

Author: Nicholas Lawrance (nicholas.lawrance@mavt.ethz.ch)

"""

plt.rc('font', **{'family': 'serif', 'sans-serif': ['Computer Modern Roman']})
plt.rc('text', usetex=True)
cmap = cm.viridis

parser = argparse.ArgumentParser(description='Plot the config space from Fig 6.1 in Intro to AMR textbook')
parser.add_argument('-nx', type=int, default=101, help='Resolution (n points in each dimension')
parser.add_argument('-sa', '--save-animation', action='store_true', help='Save animation')
args = parser.parse_args()


def make_rectangle_obstacle(xlim, ylim):
    return poly.Polygon([[xlim[0], ylim[0]], [xlim[1], ylim[0]], [xlim[1], ylim[1]], [xlim[0], ylim[1]]])


def angle_wrap(angles):
    return angles % (2 * np.pi)


def linear_path(points, nx=50):
    c_point = points[0]
    path = np.array([c_point])

    for end_point in points[1:]:
        new_path = np.linspace(path[-1], end_point, nx)       # Requires numpy > 1.16.0
        path = np.concatenate((path, new_path[1:]))

    return path



def plot_config_space(ax, obstacles, arm, cspace_array, col_map, xlim, ylim, theta1_lim, theta2_lim):
    h_obs = []
    for o in obstacles:
        h_obs.append(PlotPolygon(o, zorder=1))
    c_obs = PatchCollection(h_obs)
    # This sets colors for some reason (command in Polygon does not)
    c_obs.set_array(np.linspace(0, 1.0, len(obstacles) + 1)[1:])
    ax[0].add_collection(c_obs)

    h_arm, = ax[0].plot(*arm.get_spine_points(), c='black', lw=3.0)

    for a in ax:
        a.set_aspect('equal')

    ax[0].set_xlabel(r'$x$')
    ax[0].set_ylabel(r'$y$')
    ax[0].set_xlim(xlim)
    ax[0].set_ylim(ylim)

    ax[1].set_xlabel(r'$\theta_1$')
    ax[1].set_ylabel(r'$\theta_2$')
    ax[1].set_xlim(theta1_lim[0], theta1_lim[-1])
    ax[1].set_ylim(theta2_lim[0], theta2_lim[-1])

    # This is a bit dumb, should probably just assume [0, 2pi) everywhere, but meh
    ax[1].set_xticks([0, np.pi / 2, np.pi, 3 * np.pi / 2, 2 * np.pi])
    ax[1].set_yticks([0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi])

    ax[1].set_xticklabels([r'$0$', r'$\pi/2$', r'$\pi$', r'3$\pi/2$', r'$2\pi$'])
    ax[1].set_yticklabels([r'$0$', r'$\pi/2$', r'$\pi$', r'3$\pi/2$', r'$2\pi$'])

    cspace_array = np.ma.masked_where(cspace_array == 0.0, cspace_array)
    col_map.set_bad(color='white')
    ax[1].imshow(cspace_array.transpose(), origin='lower', cmap=col_map,
                 extent=[theta1_lim[0], theta1_lim[1], theta2_lim[0], theta2_lim[1]])

    return h_arm


class ArmAnimator(object):
    h_arm = None
    plot_artists = []

    def __init__(self, arm, obstacles, cspace_array, path, x_lim, y_lim, t1_lim, t2_lim, col_map=cm.viridis):

        self.fig, self.ax = plt.subplots(1, 2)
        self.fig.set_size_inches([9.6, 5.4])  # 1920*1080 at 200 dpi
        self.arm = arm
        self.obstacles = obstacles
        self.cspace_array = cspace_array
        self.path = path
        self.cmap = col_map
        self.x_lim = x_lim
        self.y_lim = y_lim
        self.t1lim = t1_lim
        self.t2lim = t2_lim
        self.max_frames = self.path.shape[0]
        self.end_effector_path = poly.PointList([])

    def init_fig(self):
        for a in self.ax:
            a.cla()

        self.arm.set_link_angles(self.path[0])
        self.h_arm = plot_config_space(self.ax, self.obstacles, self.arm, self.cspace_array, self.cmap, self.x_lim,
                                       self.y_lim, self.t1lim, self.t2lim)

        self.last_break = 0
        self.h_path, = self.ax[1].plot(self.path[:1, 0], self.path[:1, 1], 'r--')
        self.h_pathend, = self.ax[1].plot(self.path[0, 0], self.path[0, 1], 'ro')

        self.end_effector_path = poly.PointList([self.arm.get_end_effector_position()])
        self.h_ee_path, = self.ax[0].plot([self.end_effector_path[0].x], [self.end_effector_path[0].y], 'r--')
        self.h_ee_pathend, = self.ax[0].plot([self.end_effector_path[0].x], [self.end_effector_path[0].y], 'ro')
        self.plot_artists = [self.h_arm, self.h_path, self.h_pathend, self.h_ee_path, self.h_ee_pathend]

        return self.plot_artists

    def animate(self, i):
        self.arm.set_link_angles(self.path[i])

        self.h_arm.set_data(*self.arm.get_spine_points())
        if any(abs(self.path[i] - self.path[i-1]) > np.pi):
            old_path, = self.ax[1].plot(self.path[self.last_break:i, 0], self.path[self.last_break:i, 1], 'r--')
            self.plot_artists.append(old_path)
            self.last_break = i

        self.h_path.set_data(self.path[self.last_break:(i+1), 0], self.path[self.last_break:(i+1), 1])
        self.h_pathend.set_data(self.path[i, 0], self.path[i, 1])

        self.end_effector_path.append(self.arm.get_end_effector_position())
        self.h_ee_path.set_data(*self.end_effector_path.get_xy())
        self.h_ee_pathend.set_data([self.end_effector_path[-1].x], [self.end_effector_path[-1].y])

        return self.plot_artists


# Generate obstacles (or add your own, maybe make this a yaml input?)
ob1 = make_rectangle_obstacle([2.3, 3.4], [7, 9.8])
ob2 = make_rectangle_obstacle([7.3, 8.5], [7.6, 10])
ob3 = make_rectangle_obstacle([1.3, 3], [2.8, 3.8])
ob4 = make_rectangle_obstacle([5, 7.1], [0.9, 3.7])

all_obstacles = [ob1, ob2, ob3, ob4]

robot_arm = robot_tools.RobotArm2D(base_position=[5.0, 5.0], link_lengths=[2.1, 2.1])

theta1, theta2 = np.linspace(0, 2.0*np.pi, args.nx), np.linspace(0, 2.0*np.pi, args.nx)
v = np.zeros((len(theta1), len(theta2)), dtype=int)

for i, t1 in enumerate(theta1):
    for j, t2 in enumerate(theta2):
        robot_arm.set_link_angles([t1, t2])
        in_obs = 0
        fp = robot_arm.get_current_polygon()
        for o_num, o in enumerate(all_obstacles):
            if fp.intersect(o):
                in_obs = o_num+1
                break
        v[i, j] = in_obs

f1, a1 = plt.subplots(1, 2)
robot_arm.set_link_angles([1.1, 0.3])
plot_config_space(a1, all_obstacles, robot_arm, v, cmap, [0, 10], [0, 10], theta1[[0, -1]], theta2[[0, -1]])

# Path from textbook
path_fit = np.polyfit([0.3, 1.6, 4.3, 5.9], [1.2, 0.8, 3.3, 3.2], 3)
path_theta2 = np.linspace(0.3, 5.9, 300)
path_theta1 = np.polyval(path_fit, path_theta2)
p_full = angle_wrap(np.array([path_theta1, path_theta2]).T)

# Piecewise linear path
# p_full = angle_wrap(linear_path([[1.2, 0.3], [2.5, -2.4], [4, -2.4], [3.2, -0.2]], 100))

a1[1].plot(p_full[:, 0], p_full[:, 1], 'r--')

## Animation
animation_length = 10.0
arm_anim = ArmAnimator(robot_arm, all_obstacles, v, p_full, [0, 10], [0, 10], theta1[[0, -1]], theta2[[0, -1]])
delta_t = (animation_length * 1000.0 / arm_anim.max_frames)
arm_animation = animation.FuncAnimation(arm_anim.fig, arm_anim.animate, init_func=arm_anim.init_fig, frames=arm_anim.max_frames,
                          interval=delta_t, blit=True)

if args.save_animation:
    # animation.save('fig/arm_config_space_video.gif', writer='imagemagick', fps=1000.0/delta_t)
    arm_animation.save('fig/arm_config_space_video2.mp4', writer='ffmpeg', fps=int(1000.0/delta_t), dpi=200,
                       extra_args=["-crf", "18", "-profile:v", "main", "-tune", "animation", "-pix_fmt", "yuv420p"])
plt.show()