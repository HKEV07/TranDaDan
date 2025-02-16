import {axiosInstance} from './axiosInstance';


const sendFriendReq = async (username) => {
  try {
    const response = await axiosInstance.post('api/friend/request', {username});
    return response.data;
  } catch (error) {
    console.error('Error sending friend request:', error);
    throw error;
  }
};

const acceptFriendReq = async (username) => {
  try {
    const response = await axiosInstance.get('api/friend/acceptrequest/' + username);
    return response.data;
  } catch (error) {
    console.error('Error accepting friend request:', error);
    throw error;
  }
};

const cancelFriendReq = async (username) => {
  try {
    const response = await axiosInstance.delete('api/friend/deleterequest', {data : {username}});
    return response.data;
  } catch (error) {
    console.error('Error deleting friend request:', error);
    throw error;
  }
};

const unfriendReq = async (username) => {
  try {
    const response = await axiosInstance.delete('api/friend/unfriendrequest', {data : {username}});
    return response.data;
  } catch (error) {
    console.error('Error unfriend request:', error);
    throw error;
  }
};

export {sendFriendReq, cancelFriendReq, acceptFriendReq, unfriendReq}