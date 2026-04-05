/**
 * useUserProfile — manages the stable user identity and profile.
 *
 * - Generates a UUID on first visit and stores it in localStorage
 * - Fetches the stored profile from the API on mount
 * - Exposes profile data for pre-populating questions in both chat and wizard
 */

import { useState, useEffect, useCallback } from 'react';
import { getUserProfile, upsertUserProfile, deleteUserProfile } from '../utils/api';

const USER_ID_KEY = 'pha_user_id';

function getOrCreateUserId() {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

export default function useUserProfile() {
  const [userId] = useState(() => getOrCreateUserId());
  const [profile, setProfile] = useState(null);
  const [isReturningUser, setIsReturningUser] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getUserProfile(userId)
      .then((data) => {
        if (data?.profile) {
          setProfile(data.profile);
          setIsReturningUser(true);
        }
      })
      .catch(() => {
        // New user — 404 is expected
        setIsReturningUser(false);
      })
      .finally(() => setIsLoading(false));
  }, [userId]);

  const refreshProfile = useCallback(() => {
    getUserProfile(userId)
      .then((data) => { if (data?.profile) setProfile(data.profile); })
      .catch(() => {});
  }, [userId]);

  const clearProfile = useCallback(async () => {
    await deleteUserProfile(userId).catch(() => {});
    setProfile(null);
    setIsReturningUser(false);
    localStorage.removeItem(USER_ID_KEY);
  }, [userId]);

  return { userId, profile, isReturningUser, isLoading, refreshProfile, clearProfile };
}
