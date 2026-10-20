# Plant frontend and driver boundary

The current frontend/driver target is the original-reference CartPole host simulation; E01/E02 define its deployment boundary and replay, P13 adds transport/board software. Custom surface/EvoGym local sensor/actuator frontends are post-FPGA extensions. Keep units, sites, timing/pacing, limits, clocks/reset and overload explicit; do not substitute stock Gym defaults.

The frontend supplies environment observations and applies actuator outputs; it must not compute desired policy actions or repair the controller's organization. Historical Hanoi integrations remain historical assets. Vendor/board software is isolated from the portable core.
