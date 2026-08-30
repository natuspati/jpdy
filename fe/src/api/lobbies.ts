import { z } from 'zod';

import {
  ActiveLobby,
  LobbyDetails,
  LobbyFilter,
  LobbyInDB,
  LobbyUpdate,
  LobbyWithCategories,
  MyLobby,
  PaginatedLobbies,
} from '@/schemas';
import { request } from './http';

export async function searchLobbies(filters: Partial<LobbyFilter>) {
  return request('/lobby', PaginatedLobbies, { search: filters });
}

export async function getLobby(id: number) {
  return request(`/lobby/${id}`, LobbyDetails);
}

export async function getActiveLobbies() {
  return request('/lobby/active', z.array(ActiveLobby));
}

export async function getMyLobbies() {
  return request('/lobby/mine', z.array(MyLobby));
}

export async function createLobby() {
  return request('/lobby', LobbyInDB, { method: 'POST' });
}

export async function updateLobby(id: number, payload: LobbyUpdate) {
  return request(`/lobby/${id}`, LobbyWithCategories, { method: 'PATCH', body: payload });
}

export async function deleteLobby(id: number) {
  return request(`/lobby/${id}`, z.void(), { method: 'DELETE' });
}
