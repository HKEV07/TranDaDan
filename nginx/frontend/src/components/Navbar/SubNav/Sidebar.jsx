import React from "react";
import { Link, useNavigate } from "react-router-dom";

const Sidebar = React.forwardRef(({ isVisible }, ref) => {
  const navigate = useNavigate();
  return isVisible ? (
    <div
      id="sidebar"
      className="bg-gray-900 text-teal-200 w-64 font-pixel h-full shadow-2xl fixed top-0 left-0 z-10 border-r-2 border-pink-500"
      ref={ref}
    >
      <div className="p-4 ">
        <p className="text-2xl font-extrabold text-center mb-6 text-indigo-50">
          TranDaDan
        </p>
        <ul>
          <li className="py-3 px-4 hover:bg-pink-500 hover:text-gray-900 rounded-md transition duration-300">
            <button
              onClick={() => navigate("/")}
              className="w-full text-left"
            >
              Home
            </button>
          </li>
          <li className="py-3 px-4 hover:bg-pink-500 hover:text-gray-900 rounded-md transition duration-300">
            <button
              onClick={() => navigate("/game-lobby")}
              className="w-full text-left"
            >
              Game Mode
            </button>
          </li>
          <li className="py-3 px-4 hover:bg-pink-500 hover:text-gray-900 rounded-md transition duration-300">
            <button
              onClick={() => navigate("/dashboard")}
              className="w-full text-left"
            >
              Dashboard
            </button>
          </li>
          <li className="py-3 px-4 hover:bg-pink-500 hover:text-gray-900 rounded-md transition duration-300">
            <button
              onClick={() => navigate("/chat")}
              className="w-full text-left"
            >
              Live Chat
            </button>
          </li>
        </ul>
      </div>
    </div>
  ) : null;
});

export default Sidebar;
