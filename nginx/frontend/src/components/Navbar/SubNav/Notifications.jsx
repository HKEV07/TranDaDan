import React, { useRef, useState } from 'react';
import { useRealTime } from '../../../context/RealTimeContext.jsx'; // Import the context
import NotifDropdown from './NotifDropdown';
import { useClickOutside } from '../../../hooks/useClickOutside';

const Notifications = () => {
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef(null);
  const buttonRef = useRef(null);
  const { notifications } = useRealTime();  // Access notifications from context

  useClickOutside([notifRef, buttonRef], () => setNotifOpen(false));

  return (
    <div className="relative">
      <button
        id="notificationButton"
        ref={buttonRef}
        className="focus:outline-none"
        onClick={() => setNotifOpen((prev) => !prev)}
      >
        <svg
          className="w-8 h-8 sm:w-10 sm:h-10 text-gray-400 hover:text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.132V11a6 6 0 10-12 0v3.132a2.032 2.032 0 01-.595 1.463L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          ></path>
        </svg>
      </button>
      <NotifDropdown isVisible={notifOpen} ref={notifRef} />
      {/* Optionally, show a count of unread notifications */}
      {notifications.filter((notif) => !notif.read_at).length > 0 && (
        <span className="absolute top-0 right-0 w-4 h-4 bg-red-500 text-white rounded-full text-xs flex items-center justify-center">
          {notifications.filter((notif) => !notif.read_at).length}
        </span>
      )}
    </div>
  );
};

export default Notifications;
