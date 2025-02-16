import { useState, useEffect } from "react";
import {getMyData} from "../../api/authServiceMe";
import {getMatches, getDash} from "../../api/gameService"
import { useNavigate } from 'react-router-dom';
import Loading from "../../components/Loading/Loading";
import {MyLine, MyPie, UserLevelBox} from "../../components/user/dashboard"
import { useRealTime } from "../../context/RealTimeContext";
import {myToast} from "../../lib/utils1"

const Profile = () => {

  const navigate = useNavigate();

  const [mydata, setMyData] = useState(null);
  const [dash, setDash] = useState(null);
  const [mymatches, setMymatches] = useState(null);
  const {friends} = useRealTime();

  useEffect(() => {

    const fetchUserData = async () => {
      try {
        const data = await getMyData();
        setMyData(data);
        const matches = await getMatches(data.id);
        const dash_data = await getDash(data.id);
        setDash(dash_data);
        setMymatches(matches);
      } catch (error) {
        myToast(2, "some thing went wrong.");
        navigate('/')
      }
    };

    fetchUserData();
  }, [friends]);

  if (!mydata || !mymatches || !dash) return <Loading />

  return (
    <div className="flex flex-col items-center min-h-screen bg-cover bg-center bg-[url('/retro_1.jpeg')] from-darkBackground via-purpleGlow to-neonBlue text-white font-retro">
      <div className="flex flex-wrap m-10 justify-between w-11/12 gap-4 mt-20">
        <div className="flex-1 min-w-[500px] h-[500px] p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonBlue shadow-[0_0_25px_5px] shadow-neonBlue">
          <div className="flex flex-col items-center">
            <img
              src={mydata.avatar_url || '/default_profile.webp'}
              alt="Profile"
              className="w-36 h-36 rounded-full border-4 border-white shadow-[0_0_20px_5px] shadow-neonPink mb-4"
            />
            {/* <h2 className="text-3xl text-center text-neonPink">username</h2> */}
            <p
              className="text-center text-3xl text-gray-200 mt-4"
              style={{ textShadow: "1px 1px 5px rgb(0, 0, 0)" }}
            >
              {mydata.username}
            </p>
            <p className="text-center text-neonBlue mt-2 text-xl">
              {mydata.email}
            </p>

            <button
              onClick={() => (navigate("/Profile/edit"))}
              className="mt-4 px-6 py-2 bg-neonPink text-black font-bold rounded-lg shadow-[0_0_10px_2px] shadow-neonPink hover:shadow-[0_0_15px_3px] transition-all"
            >
              Edit Profile
            </button>
          </div>
        </div>

        <UserLevelBox progress={mydata.xp_progress} level={mydata.level} />

        <div className="flex-1 min-w-[600px] h-[500px] p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonPink shadow-[0_0_25px_5px] shadow-neonPink overflow-y-auto">
          <h2 className="text-2xl text-center text-neonPink mb-4">Friends</h2>
          {mydata.friends && mydata.friends.length > 0 ? (
              <ul className="space-y-4">
                {mydata.friends.map((friend) => (
                  <li
                  key={friend.id}
                  className="flex items-center justify-between gap-4 p-3 bg-gradient-to-r from-purple-700 via-pink-400 to-purple-700 rounded-lg border-2 border-neonPink shadow-lg hover:shadow-2xl transition-shadow duration-300"
                >
                  <div className="flex items-center gap-4">
                    <img
                      src={friend.avatar_url || '/default_profile.webp'}
                      alt={`${friend.username}'s avatar`}
                      className="w-12 h-12 rounded-full border-4 border-white shadow-[0_0_10px_2px] shadow-neonPink"
                    />
                    <a href="#" onClick={() => navigate(`/user/${friend.username}`)}>
                      <p className="text-lg text-white font-medium text-shadow-lg hover:text-neonPink transition-colors">
                        {friend.username}
                      </p>
                    </a>
                  </div>
                  <div className="text-lg font-bold text-white">
                    <span className="text-gl text-neonPink">Level </span>
                    <span className="text-xl text-neonBlue">{friend.level}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-center text-gray-400">No friends to display.</p>
          )}
        </div>

        <div className="flex-1 min-w-[600px] min-h-[500px] h-fit p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonPink shadow-[0_0_25px_5px] shadow-neonPink">
        <p className="text-3xl text-center text-neonBlue mb-5">PingPong</p>
          <h2 className="text-2xl text-center text-neonPink mb-4">Match History</h2>
          <div className="overflow-x-auto h-72 overflow-y-auto">
          {mymatches.pong && mymatches.pong.length > 0 ? (
            <table className="w-full text-center text-white border-collapse">
              <thead>
                <tr className="bg-neonBlue text-black">
                  <th className="p-2 border border-white">#</th>
                  <th className="p-2 border border-white">Date</th>
                  <th className="p-2 border border-white">Opponent</th>
                  <th className="p-2 border border-white">Result</th>
                  <th className="p-2 border border-white">Score</th>
                </tr>
              </thead>
              <tbody>
                {mymatches.pong.map((match) => (
                  <tr key={match.id} className="odd:bg-gray-800 even:bg-gray-700">
                    <td className="p-2 border border-white">{match.id}</td>
                    <td className="p-2 border border-white">{match.end_date}</td>
                    <td className="p-2 border border-white">{match.opponent}</td>
                    <td className="p-2 border border-white">{match.result}</td>
                    <td className="p-2 border border-white">{match.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            ):(
              <p className="text-center text-gray-400">No matches to display.</p>
            )}
          </div>
        </div>

        <div className="flex-1 min-w-[600px] min-h-[500px] h-fit p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonPink shadow-[0_0_25px_5px] shadow-neonPink">
          <p className="text-3xl text-center text-red-600 mb-5">SPACExRIVALRY</p>
          <h2 className="text-2xl text-center text-neonPink mb-4">Match History</h2>
          <div className="overflow-x-auto h-72 overflow-y-auto">
          {mymatches.space && mymatches.space.length > 0 ? (
            <table className="w-full text-center text-white border-collapse">
              <thead>
                <tr className="bg-neonBlue text-black">
                  <th className="p-2 border border-white">#</th>
                  <th className="p-2 border border-white">Date</th>
                  <th className="p-2 border border-white">Opponent</th>
                  <th className="p-2 border border-white">Result</th>
                  <th className="p-2 border border-white">Score</th>
                </tr>
              </thead>
              <tbody>
                {mymatches.space.map((match) => (
                  <tr key={match.id} className="odd:bg-gray-800 even:bg-gray-700">
                    <td className="p-2 border border-white">{match.id}</td>
                    <td className="p-2 border border-white">{match.end_date}</td>
                    <td className="p-2 border border-white">{match.opponent}</td>
                    <td className="p-2 border border-white">{match.result}</td>
                    <td className="p-2 border border-white">{match.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            ):(
              <p className="text-center text-gray-400">No matches to display.</p>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap justify-between w-11/12 gap-4 mb-4">
        <div className="flex-1 min-w-[500px] h-[500px] p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonBlue shadow-[0_0_25px_5px] shadow-neonBlue">
          <p className="text-3xl text-center text-neonBlue mb-5">PingPong</p>
          <h1 className="text-center text-2xl m-2"><span className="text-red-700">Lose</span> and <span className="text-neonBlue">Win</span> rate.</h1>
          <div className="w-full h-[350px] flex items-center justify-center">
            <MyPie data={dash.pong}/>
          </div>
        </div>
        <div className="flex-1 min-w-[500px] h-[500px] p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonBlue shadow-[0_0_25px_5px] shadow-neonBlue">
          <p className="text-3xl text-center text-red-600 mb-5">SPACExRIVALRY</p>
          <h1 className="text-center text-2xl m-2"><span className="text-red-700">Lose</span> and <span className="text-neonBlue">Win</span> rate.</h1>
          <div className="w-full h-[350px] flex items-center justify-center">
            <MyPie data={dash.space}/>
          </div>
        </div>
        <div className="flex-1 min-w-[500px] h-[500px] p-6 bg-black bg-opacity-80 rounded-lg border-2 border-neonBlue shadow-[0_0_25px_5px] shadow-neonBlue">
          <h1 className="text-center text-2xl m-2"><span className="text-red-700">Lose</span> and <span className="text-neonBlue">Win</span> rate.</h1>
          <div className="w-full h-[350px] flex items-center justify-center">
          <MyLine data={dash}/>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
