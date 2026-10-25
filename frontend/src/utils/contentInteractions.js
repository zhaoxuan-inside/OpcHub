/**
 * Unified public-content interaction helpers.
 *
 * Lists are served from server-side caches that intentionally do not contain
 * per-viewer interaction state. After a list arrives we batch-read the unified
 * counters + viewer toggles and merge them onto the same item objects, so every
 * card renders one consistent interaction model.
 */
import { dispatchGateway } from '@/api/gateway';

export async function enrichInteractions(items, targetType, options = {}) {
  const { idKey = 'id', silent = true } = options;
  if (!Array.isArray(items) || items.length === 0) return items;

  const valid = items.filter((item) => item && item[idKey] !== undefined && item[idKey] !== null);
  if (valid.length === 0) return items;

  const targets = valid.map((item) => ({
    target_type: targetType,
    target_id: String(item[idKey]),
  }));

  try {
    const res = await dispatchGateway(
      'content.interactions.state',
      { targets },
      { silent }
    );
    if (!res.ok || !res.data || !Array.isArray(res.data.items)) return items;

    const byId = new Map();
    for (const state of res.data.items) {
      byId.set(String(state.target_id), state);
    }

    for (const item of valid) {
      const state = byId.get(String(item[idKey]));
      if (!state) continue;
      applyInteractionState(item, state);
    }
  } catch (e) {
    // Public reads must never block the page; cards fall back to legacy counters.
  }
  return items;
}

export function applyInteractionState(item, state) {
  if (!item || !state) return item;
  item.like_count = Number(state.like_count || 0);
  item.favorite_count = Number(state.favorite_count || 0);
  item.love_count = Number(state.love_count || 0);
  item.comment_count = Number(state.comment_count || 0);
  item.dislike_count = Number(state.dislike_count || 0);
  item.rating_avg = Number(state.rating_avg || 0);
  item.rating_count = Number(state.rating_count || 0);
  item.viewer = {
    liked: Boolean(state.viewer?.liked),
    favorited: Boolean(state.viewer?.favorited),
    loved: Boolean(state.viewer?.loved),
    commented: Boolean(state.viewer?.commented),
    disliked: Boolean(state.viewer?.disliked),
    rating: Number(state.viewer?.rating || 0),
  };
  return item;
}

/** Apply the change emitted by ContentInteractionBar back onto a list item. */
export function applyBarChange(item, payload) {
  if (!item || !payload) return item;
  item.like_count = Number(payload.like_count || 0);
  item.favorite_count = Number(payload.favorite_count || 0);
  item.love_count = Number(payload.love_count || 0);
  item.comment_count = Number(payload.comment_count || 0);
  item.dislike_count = Number(payload.dislike_count || 0);
  item.rating_avg = Number(payload.rating_avg || 0);
  item.rating_count = Number(payload.rating_count || 0);
  item.viewer = {
    liked: Boolean(payload.viewer?.liked),
    favorited: Boolean(payload.viewer?.favorited),
    loved: Boolean(payload.viewer?.loved),
    commented: Boolean(payload.viewer?.commented),
    disliked: Boolean(payload.viewer?.disliked),
    rating: Number(payload.viewer?.rating || 0),
  };
  return item;
}

/**
 * Forum cards keep legacy field names (replies / bookmark_count) for sorting and
 * detail navigation. 赞同/反对 (upvotes / user_vote) is the forum domain's own vote
 * ledger and is never aliased from the unified counters.
 */
export function applyForumInteractionAliases(post) {
  if (!post) return post;
  const viewer = post.viewer || {};
  post.replies = Number(post.comment_count || 0);
  post.bookmark_count = Number(post.favorite_count || 0);
  post.is_bookmarked = Boolean(viewer.favorited);
  post.is_loved = Boolean(viewer.loved);
  post.is_commented = Boolean(viewer.commented);
  return post;
}

export async function enrichForumInteractions(posts) {
  await enrichInteractions(posts, 'FORUM_THREAD');
  if (Array.isArray(posts)) {
    posts.forEach(applyForumInteractionAliases);
  }
  return posts;
}
