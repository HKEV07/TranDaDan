import {axiosInstance} from './axiosInstance';


const blockUser = async (username) => {
  try {
    const response = await axiosInstance.post('/api/blockuser', {username});
    return response.data;
  } catch (error) {
    console.error('Error block user request:', error);
    throw error;
  }
};

const unblockUser = async (username) => {
  try {
    const response = await axiosInstance.delete('/api/blockuser', {data : {username}});
    return response.data;
  } catch (error) {
    console.error('Error unblock user request:', error);
    throw error;
  }
};

export {blockUser, unblockUser}