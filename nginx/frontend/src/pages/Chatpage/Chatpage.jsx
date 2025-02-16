import React, { useState, useEffect, useCallback, useRef } from "react";
import { useUser } from "../../components/auth/UserContext";
import ChatContent from "../../components/chat/ChatWin/ChatContent";
import UserList from "../../components/chat/ChatWin/UserList";
import getAllMessage from "../../api/axiosGetallMessage";
import styles from "../../components/chat/styles.module.scss";
import { useWebSocket } from "../../chatContext/WebSocketContext";
import { useRealTime } from "../../context/RealTimeContext"
import getUserData from "../../api/authServiceUser";

const ChatApp = () => {
  const { user, isAuthenticated } = useUser();
  const { sendMessage, registerMessageHandler, isConnected } = useWebSocket();
  const [messages, setMessages] = useState([]);
  const [friendsData, setFriendsData] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const wasAtBottomRef = useRef(false);
  const messageIdsRef = useRef(new Set());
  const lastMessageLoadingRef = useRef(new Set());
  const pageTrackingRef = useRef(new Map());
  const messageCacheRef = useRef(new Map());
  const lastMessagesRef = useRef(new Map());
  const { friends } = useRealTime()

  const currentUsername = user ? JSON.parse(user).username : null;

  const generateMessageId = useCallback((sender, timestamp) => {
    return `${sender}-${timestamp}-${Math.random().toString(36).slice(2, 9)}`;
  }, []);

  const cacheMessages = useCallback((chatId, messages, page) => {
    const currentCache = messageCacheRef.current.get(chatId) || [];
    const newCache = [...currentCache];

    messages.forEach((msg) => {
      const index = newCache.findIndex((m) => m.id === msg.id);
      if (index === -1) {
        newCache.push(msg);
      }
    });

    messageCacheRef.current.set(
      chatId,
      newCache.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    );

    pageTrackingRef.current.set(
      chatId,
      new Set([...(pageTrackingRef.current.get(chatId) || new Set()), page])
    );
  }, []);

  const updateFriendLastMessage = useCallback(
    (friendName, newMessage) => {
      lastMessagesRef.current.set(friendName, {
        content: newMessage.text,
        timestamp: newMessage.timestamp,
      });

      setFriendsData((prevFriends) =>
        prevFriends.map((friend) => {
          if (friend.name === friendName) {
            const isMessageFromMe = newMessage.sender === currentUsername;
            const isSelectedChat = friend.id === selectedChat;

            const shouldIncrementUnread = !isMessageFromMe && !isSelectedChat;

            return {
              ...friend,
              lastMessage: newMessage.text,
              lastMessageTime: newMessage.timestamp,
              lastMessageSender: newMessage.sender,
              unreadCount: shouldIncrementUnread
                ? (friend.unreadCount || 0) + 1
                : friend.unreadCount || 0,
            };
          }
          return friend;
        })
      );
    },
    [selectedChat, currentUsername]
  );

  const handleChatSelection = useCallback((chatId) => {
    setFriendsData((prevFriends) =>
      prevFriends.map((friend) =>
        friend.id === chatId ? { ...friend, unreadCount: 0 } : friend
      )
    );
    setSelectedChat(chatId);
  }, []);

  useEffect(() => {
    loadFriendsWithLastMessages();
  }, [friends])

  const loadFriendsWithLastMessages = async () => {
    if (!isAuthenticated) return;

    try {
      setIsLoading(true);

      const avatarPromises = new Map();

      for (const friend of friends) {
        avatarPromises.set(
          friend,
          getUserData(friend).catch(error => {
            console.error(`Error fetching avatar for ${friend}:`, error);
            return null;
          })
        );
      }

      const avatarResults = await Promise.allSettled(Array.from(avatarPromises.values()));
      const newAvatarMap = new Map();

      friends.forEach((friend, index) => {
        const avatarResult = avatarResults[index];
        const avatarUrl = avatarResult.status === 'fulfilled' && avatarResult.value
          ? avatarResult.value.avatar_url
          : 'default-avatar-url';
        newAvatarMap.set(friend, avatarUrl);
      });

      const friendsData = friends.map((friend, index) => {
        const cachedLastMessage = lastMessagesRef.current.get(friend);
        return {
          id: index + 1,
          name: friend,
          online: false,
          lastSeen: new Date().toISOString(),
          avatar: newAvatarMap.get(friend),
          lastMessage: cachedLastMessage?.content || null,
          lastMessageTime: cachedLastMessage?.timestamp || null,
          unreadCount: 0,
        };
      });

      setFriendsData(friendsData);

      const uncachedFriends = friendsData.filter(
        (friend) => !lastMessagesRef.current.has(friend.name)
      );

      if (uncachedFriends.length > 0) {
        await loadLastMessagesForFriends(uncachedFriends);
      }
    } catch (error) {
      setError("Failed to load friends list. Please refresh the page.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadLastMessagesForFriends = async (friendsToLoad) => {
    for (const friend of friendsToLoad) {
      if (lastMessageLoadingRef.current.has(friend.name)) continue;

      lastMessageLoadingRef.current.add(friend.name);

      try {
        const response = await getAllMessage(`${friend.name}?page=1`);
        if (!response.results || response.results.length === 0) {
          lastMessagesRef.current.set(friend.name, {
            content: null,
            timestamp: null,
          });
          continue;
        }

        const lastMessage = response.results[0];
        lastMessagesRef.current.set(friend.name, {
          content: lastMessage.content,
          timestamp: lastMessage.timestamp,
        });

        setFriendsData((prev) =>
          prev.map((f) =>
            f.name === friend.name
              ? {
                ...f,
                lastMessage: lastMessage.content,
                lastMessageTime: lastMessage.timestamp,
              }
              : f
          )
        );
      } catch (error) {
        console.error(`Error loading messages for ${friend.name}:`, error);
      } finally {
        lastMessageLoadingRef.current.delete(friend.name);
      }
    }
  };

  const saveScrollPosition = useCallback(() => {
    if (selectedChat) {
      const chatBody = document.querySelector(".chat-body");
      if (chatBody) {
        const isAtBottom =
          Math.abs(
            chatBody.scrollHeight - chatBody.scrollTop - chatBody.clientHeight
          ) < 10;
        wasAtBottomRef.current = isAtBottom;
        scrollPositionRef.current = 0;
      }
    }
  }, [selectedChat]);

  const restoreScrollPosition = useCallback(() => {
    const chatBody = document.querySelector(".chat-body");
    if (!chatBody) return;

    if (wasAtBottomRef.current) {
      chatBody.scrollTop = chatBody.scrollHeight;
    } else if (scrollPositionRef.current !== null) {
      chatBody.scrollTop = scrollPositionRef.current;
    }
  }, []);

  const loadMoreMessages = async () => {
    if (!selectedChat || isLoadingMore || !hasMore) return;

    try {
      setIsLoadingMore(true);
      saveScrollPosition();

      const selectedFriend = friendsData.find((f) => f.id === selectedChat);
      if (!selectedFriend) return;

      const loadedPages =
        pageTrackingRef.current.get(selectedChat) || new Set([1]);
      const nextPage = Math.max(...Array.from(loadedPages)) + 1;

      const currentMessages = messageCacheRef.current.get(selectedChat);
      if (!currentMessages || currentMessages.length === 0) {
        setHasMore(false);
        return;
      }

      if ((nextPage - 1) * 50 > currentMessages.length) {
        setHasMore(false);
        return;
      }

      const response = await getAllMessage(
        `${selectedFriend.name}?page=${nextPage}`
      );

      const formattedMessages = response.results.map((msg) => ({
        id: generateMessageId(msg.sender, msg.timestamp),
        text: msg.content,
        sender: msg.sender,
        timestamp: msg.timestamp,
      }));

      cacheMessages(selectedChat, formattedMessages, nextPage);

      setMessages((prev) => {
        const allMessages = [...prev, ...formattedMessages];
        return Array.from(
          new Map(allMessages.map((msg) => [msg.id, msg])).values()
        ).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      });

      setHasMore(response.next !== null);

      requestAnimationFrame(() => {
        restoreScrollPosition();
      });
    } catch (error) {
      const loadedPagesArray = Array.from(
        pageTrackingRef.current.get(selectedChat)
      );
      loadedPagesArray.pop();
      pageTrackingRef.current.set(selectedChat, new Set(loadedPagesArray));
    } finally {
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    loadFriendsWithLastMessages();
    return () => {
      messageIdsRef.current.clear();
      lastMessageLoadingRef.current.clear();
      pageTrackingRef.current.clear();
      messageCacheRef.current.clear();
      lastMessagesRef.current.clear();
    };
  }, [isAuthenticated]);

  useEffect(() => {
    const loadInitialMessages = async () => {
      if (!selectedChat) return;

      setIsLoading(true);
      setHasMore(true);

      try {
        const selectedFriend = friendsData.find((f) => f.id === selectedChat);
        if (!selectedFriend) return;

        const cachedMessages = messageCacheRef.current.get(selectedChat);
        if (cachedMessages?.length) {
          setMessages(cachedMessages);
          return;
        }

        const response = await getAllMessage(`${selectedFriend.name}?page=1`);


        if (!response.results || response.results.length === 0) {
          setMessages([]);
          setHasMore(false);

          messageCacheRef.current.set(selectedChat, []);
          pageTrackingRef.current.set(selectedChat, new Set([1]));
          return;
        }

        const formattedMessages = response.results.map((msg) => ({
          id: generateMessageId(msg.sender, msg.timestamp),
          text: msg.content,
          sender: msg.sender,
          timestamp: msg.timestamp,
        }));

        const sortedMessages = formattedMessages.sort(
          (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
        );

        cacheMessages(selectedChat, sortedMessages, 1);
        setMessages(sortedMessages);
        setHasMore(response.next !== null);

        setFriendsData((prev) =>
          prev.map((friend) =>
            friend.id === selectedChat ? { ...friend, unreadCount: 0 } : friend
          )
        );
      } catch (error) {
        console.error("Error loading messages:", error);
        setError("Failed to load message history. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    loadInitialMessages();
  }, [selectedChat, friendsData, generateMessageId, cacheMessages]);

  useEffect(() => {
    const handleMessage = (data) => {
      if (data.error) {
        setError(data.error);
        return;
      }

      if (data.message && data.sender) {
        const messageId = generateMessageId(data.sender, Date.now());
        if (messageIdsRef.current.has(messageId)) return;

        messageIdsRef.current.add(messageId);

        const newMsg = {
          id: messageId,
          text: data.message,
          sender: data.sender,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [newMsg, ...prev]);

        const friendName = data.sender === currentUsername ? data.receiver : data.sender;
        updateFriendLastMessage(friendName, newMsg);

        const chatId = friendsData.find((f) => f.name === friendName)?.id;
        if (chatId) {
          const cachedMessages = messageCacheRef.current.get(chatId) || [];
          messageCacheRef.current.set(chatId, [newMsg, ...cachedMessages]);
        }
      }
    };

    const unregister = registerMessageHandler(handleMessage);
    return () => unregister();
  }, [
    generateMessageId,
    registerMessageHandler,
    currentUsername,
    updateFriendLastMessage,
    friendsData,
  ]);

  const handleSendMessage = useCallback(
    (e) => {
      if (e) e.preventDefault();
      if (!newMessage.trim() || !selectedChat) return;

      const selectedFriend = friendsData.find((f) => f.id === selectedChat);
      if (!selectedFriend) return;

      const messageData = {
        username: selectedFriend.name,
        content: newMessage.trim(),
      };

      const timestamp = new Date().toISOString();
      const tempMessage = {
        id: generateMessageId(currentUsername, timestamp),
        text: newMessage.trim(),
        sender: currentUsername,
        timestamp: timestamp,
        pending: true,
      };

      setMessages((prev) => [tempMessage, ...prev]);
      setNewMessage("");

      updateFriendLastMessage(selectedFriend.name, tempMessage);

      const cachedMessages = messageCacheRef.current.get(selectedChat) || [];
      messageCacheRef.current.set(selectedChat, [
        tempMessage,
        ...cachedMessages,
      ]);

      if (isConnected) {
        const sent = sendMessage(messageData);
        if (sent) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === tempMessage.id ? { ...msg, pending: false } : msg
            )
          );
        } else {
          setError("Failed to send message. Please try again.");
        }
      } else {
        setError("Connection lost. Please wait while we reconnect.");
      }
    },
    [
      selectedChat,
      newMessage,
      friendsData,
      currentUsername,
      generateMessageId,
      isConnected,
      sendMessage,
      updateFriendLastMessage,
    ]
  );

  const handleSidebarToggle = (type) => {
    setActiveSidebar(activeSidebar === type ? null : type);
  };

  return (
    <>
      <div className={`flex flex-col ${styles.nwbody}`}>
        <div className="flex">
          <div className={`${styles.chat_win}`}>

            <UserList
              friends={friendsData}
              selectedChat={selectedChat}
              setSelectedChat={handleChatSelection}
              isLoading={isLoading}
              currentUsername={currentUsername}
            />
            <ChatContent
              friends={friendsData}
              messages={messages}
              selectedChat={selectedChat}
              newMessage={newMessage}
              setNewMessage={setNewMessage}
              handleSendMessage={handleSendMessage}
              handleSidebarToggle={handleSidebarToggle}
              isOnline={friendsData.find((f) => f.id === selectedChat)?.online}
              loadMoreMessages={loadMoreMessages}
              hasMore={hasMore}
              isLoading={isLoading}
              isLoadingMore={isLoadingMore}
            />
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatApp;
