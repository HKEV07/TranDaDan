import { useState } from "react";
import { Route, BrowserRouter, Routes, Navigate } from "react-router-dom";
import Homepage from "./pages/Homepage/Homepage";
import MainLayout from "./layouts/MainLayout";
import Login from "./pages/Login/Login";
import Register from "./pages/Register/Register";
import GameMode from "./layouts/GameMode/GameMode";
import GameChoice from "./pages/GameChoice/GameChoice";
import MatchMaking from "./pages/MatchMaking/MatchMaking";
import CpuMode from "./components/Pong/CpuMode/CpuMode";
import LocalMode from "./components/Pong/LocalMode/LocalMode";
import Profile from "./pages/Profile/Profile";
import RemoteMode from "./components/Pong/RemotePlay/RemoteMode";
import IntraCallback from "./components/auth/IntraCallback";
import ChatApp from "./pages/Chatpage/Chatpage";
import { ToastContainer } from "react-toastify";
import QuadraMode from "./components/Pong/QuadraMode/QuadraMode";
import TournamentBracket from "./pages/Tournament/Tournament";
import QuadraRegister from "./pages/QuadraRegister/QuadraRegister";
import LocalRegister from "./pages/LocalRegister/LocalRegister";
import TournamentMode from "./components/Pong/TournamentMode/TournamentMode";
import RemoteRivalry from "./components/SpaceInvaders/RemoteRivalry/RemoteRivalry.jsx";
import SpaceRivalry from "./components/SpaceInvaders/SpaceRivalry/SpaceRivalry.jsx";
import InviteUI from "./components/InviteUI/InviteUI.jsx";
import ClassicPong from "./components/Pong/ClassicPong/ClassicPong.jsx";
import { TournamentProvider } from "./context/TournamentContext.jsx";
import NotFound from "./pages/NotFound/NotFound.jsx"

import User from "./pages/User/User";
import EditProfile from "./pages/EditProfile/EditProfile";
// import { Edit } from "lucide-react";
import { UserProvider } from "./components/auth/UserContext";
import { ProtectedRoute, PublicRoute } from "./components/auth/ProtectedRoute";
import { RealTimeProvider } from './context/RealTimeContext.jsx';
import { WebSocketProvider } from "./chatContext/WebSocketContext";
import ResetPasswordForm from "./pages/ResetPassword/ResetPasswordForm"
import EmailVerificationPage from "./pages/EmailVerificationPage.jsx";
import { InviteProvider } from "./chatContext/InviteContext.jsx";
import { Space } from "lucide-react";
import MatchDashboard from "./pages/Dashboard/Dashboard.jsx";

function App() {
  return (
    <BrowserRouter future={{
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    }}>
      <UserProvider>
        <WebSocketProvider>
          <RealTimeProvider>
            <ToastContainer position="top-right" autoClose={3000} />
            <Routes>
              <Route path="/" element={
                <InviteProvider>
                  <MainLayout />
                </InviteProvider>
              }>
                <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <MatchDashboard />
                  </ProtectedRoute>
                }
              />
                <Route
                path="/notfound"
                element={
                    <NotFound />
                }
              />
                <Route index element={<Homepage />} />
                <Route
                  path="/chat"
                  element={
                    <ProtectedRoute>
                      <ChatApp />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />
                <Route path="/profile/edit" element={
                  <ProtectedRoute>
                    <EditProfile />
                  </ProtectedRoute>
                } />
                <Route path="/user/:username" element={
                  <ProtectedRoute>
                    <User />
                  </ProtectedRoute>
                } />
              </Route>

              <Route
                path="/game-lobby"
                element={
                  <ProtectedRoute>
                    <GameMode />
                  </ProtectedRoute>
                }
              >
                <Route index element={<TournamentProvider><GameChoice /></TournamentProvider>} />
                <Route path="matchmaking" element={<MatchMaking />} />
                <Route path="cpu-mode" element={<CpuMode />} />
                <Route path="remote-play" element={<RemoteMode />} />
                <Route path="local-mode" element={<LocalMode />} />
                <Route path="quadra-mode" element={<QuadraMode />} />
                <Route path="tournament" element={
                  <TournamentProvider>
                    <TournamentBracket />
                  </TournamentProvider>
                } />
                <Route path="quadra-register" element={<QuadraRegister />} />
                <Route path="local-register" element={<LocalRegister />} />
                <Route path="tournament-mode" element={
                  <TournamentProvider>
                    <TournamentMode />
                  </TournamentProvider>} />
                <Route path="space-rivalry" element={<SpaceRivalry />} />
                <Route path="remote-rivalry" element={<RemoteRivalry />} />
                <Route path="classic-pong" element={<ClassicPong />} />

              </Route>
              <Route
                path="/register"
                element={
                  <PublicRoute>
                    <Register />
                  </PublicRoute>
                }
              />
              <Route
                path="/login"
                element={
                  <PublicRoute>
                    <Login />
                  </PublicRoute>
                }
              />
              <Route path="/email-verify/:token" element={
                <PublicRoute>
                  <EmailVerificationPage />
                </PublicRoute>
              }>
              </Route>
              <Route path="/Intra/callback/" element={
                <PublicRoute>
                  <IntraCallback />
                </PublicRoute>
              } />
              <Route path="/reset-password/:token" element={

                <ResetPasswordForm />
              } />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </RealTimeProvider>
        </WebSocketProvider>
      </UserProvider>
    </BrowserRouter>
  );
}

export default App;

