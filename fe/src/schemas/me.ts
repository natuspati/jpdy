import { z } from 'zod';

import { UserRole } from './enums';
import { LobbyInDB } from './lobby';
import { PromptCategoryInDB } from './prompt';

// /user/me response — mirrors UserWithPromptsLobbiesPublicSchema. Lives in
// its own file so user.ts <-> lobby.ts never form a circular import (lobby
// already depends on user.UserPublic).
export const MeResponse = z.object({
  id: z.number().int(),
  username: z.string(),
  role: UserRole,
  admin_key_attempted: z.boolean(),
  prompt_categories: z.array(PromptCategoryInDB),
  lobbies: z.array(LobbyInDB),
});
export type MeResponse = z.infer<typeof MeResponse>;
