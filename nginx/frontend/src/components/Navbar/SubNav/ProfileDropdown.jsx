import React from "react";
import styles from "./SubNav.module.scss";
import { useNavigate, Link } from "react-router-dom";
import { useUser } from "../../../components/auth/UserContext";
import { useRealTime } from "../../../context/RealTimeContext";


const ProfileDropdown = React.forwardRef(({isVisible}, ref) => {
  const { logout } = useUser();
  const navigate = useNavigate();
  const {clearRealTimeContext} = useRealTime();

  const handleLogout = () => {
    logout();
    clearRealTimeContext();
    navigate("/");
  };

  const handleNavigation = (path) => {
    navigate(path);
  };

  return (
    <div
      id="profileDropdown"
      ref={ref}
      className={`${styles.profileDropdown} ${isVisible && styles.show} absolute right-0 mt-2 w-48 bg-gray-900 text-teal-200 border-2 border-pink-500 shadow-lg rounded-md z-10`}
    >
      <a
        onClick={() => handleNavigation("/profile")}
        className="block px-4 py-2 hover:bg-pink-500 hover:text-gray-900"
      >
        My Profile
      </a>
      <a
        onClick={() => handleNavigation("/profile/edit")}
        className="block px-4 py-2 hover:bg-pink-500 hover:text-gray-900"
      >
        Settings
      </a>
      <a
        onClick={handleLogout}
        className="block px-4 py-2 hover:bg-pink-500 hover:text-gray-900"
      >
        Sign Out
      </a>
    </div>
  )
});

export default ProfileDropdown;
