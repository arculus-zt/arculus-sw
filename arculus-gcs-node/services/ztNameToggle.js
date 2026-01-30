// services/ztNameToggle.js
let SHOW_ZT_IN_DEVICE_NAME = true; // global for this Node process

function setShowZtInDeviceName(val) {
  SHOW_ZT_IN_DEVICE_NAME = !!val;
}

function getShowZtInDeviceName() {
  return SHOW_ZT_IN_DEVICE_NAME;
}

module.exports = {
  setShowZtInDeviceName,
  getShowZtInDeviceName,
};
