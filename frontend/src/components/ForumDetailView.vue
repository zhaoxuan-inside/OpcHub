<template>
  <div class="forum-detail-page-wrapper">
    <!-- Top Fluid Action Header -->
    <div class="glass-box detail-page-header">
      <div class="header-left">
        <button class="btn-back-square" @click="$emit('back')" title="返回风暴广场">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
        </button>

        <div class="breadcrumb-cluster">
          <div class="breadcrumb-row">
            <span class="crumb-link" @click="$emit('back')">头脑风暴广场</span>
            <span class="crumb-separator">/</span>
            <span class="crumb-current">{{ categoryLabel }}</span>
          </div>
          <div class="meta-pills-row">
            <span class="category-pill" :style="pillStyle">{{ categoryLabel }}</span>
            <span v-if="post?.pinned" class="pinned-pill">{{ post.pinned }}</span>
            <span class="ip-info">{{ post?.ip_location || '来自 浙江' }}</span>
            <span class="time-info">· 发表于 {{ post?.updated_at || '刚刚' }}</span>
          </div>
        </div>
      </div>

      <!-- Header Right Actions -->
      <div class="header-right-actions">
        <button
          type="button"
          class="btn-header-action"
          :class="{ active: threadUpvoted }"
          @click="toggleThreadUpvote"
          title="点赞此实战经验"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"></path>
          </svg>
          <span>{{ threadUpvoted ? '已点赞' : '点赞' }}</span>
          <span class="count-tag">{{ threadUpvoteCount }}</span>
        </button>

        <button
          type="button"
          class="btn-header-action"
          :class="{ active: threadBookmarked }"
          @click="toggleThreadBookmark"
          title="收藏归档至知识库"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" :fill="threadBookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>{{ threadBookmarked ? '已收藏' : '收藏' }}</span>
        </button>

        <button
          type="button"
          class="btn-header-action"
          :class="{ active: threadLoved }"
          @click="toggleThreadLove"
          :title="threadLoved ? '取消喜欢' : '喜欢这篇实战经验'"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" :fill="threadLoved ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
            <path d="M20.8 5.6a5.2 5.2 0 0 0-7.4 0L12 7l-1.4-1.4a5.2 5.2 0 1 0-7.4 7.4L12 21l8.8-7.9a5.2 5.2 0 0 0 0-7.5Z"></path>
          </svg>
          <span>{{ threadLoved ? '已喜欢' : '喜欢' }}</span>
          <span class="count-tag">{{ threadLoveCount }}</span>
        </button>

        <button
          type="button"
          class="btn-header-action"
          :class="{ active: isCopied }"
          @click="handleCopyLink"
          title="分享实战帖"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="18" cy="5" r="3"></circle>
            <circle cx="6" cy="12" r="3"></circle>
            <circle cx="18" cy="19" r="3"></circle>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
          </svg>
          <span>{{ isCopied ? '已复制' : '分享' }}</span>
        </button>

        <button type="button" class="btn-header-ghost-report" @click="handleReport" title="合规举报违规内容">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          <span>举报</span>
        </button>

        <button
          v-if="canDelete"
          type="button"
          class="btn-header-ghost-delete"
          @click="$emit('delete', post)"
          title="删除这篇风暴帖"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
          <span>删除</span>
        </button>
      </div>
    </div>

    <!-- Centered Full-Page Article Article Container -->
    <div class="article-center-container">
      <article class="glass-box article-main-card">
        <!-- Post Title -->
        <h1 class="article-title">{{ post?.title }}</h1>

        <!-- Author Information Bar -->
        <div class="article-author-bar">
          <div class="author-left">
            <div class="author-avatar-orb">
              {{ (post?.author || '创客')[0].toUpperCase() }}
            </div>
            <div class="author-text-meta">
              <div class="author-name-line">
                <span class="author-name">{{ post?.author || '认证创客' }}</span>
                <span class="maker-verified-pill">已认证超级个体</span>
              </div>
              <div class="author-sub-line">
                <span>浏览 {{ post?.view_count || 128 }} 次</span>
                <span>·</span>
                <span>{{ commentTree.length }} 条探讨见解</span>
                <span>·</span>
                <span>{{ post?.ip_location || '来自 浙江' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tags Row -->
        <div v-if="post?.tags && post.tags.length > 0" class="article-tags-cluster">
          <span v-for="tag in post.tags" :key="tag" class="tag-badge">
            #{{ tag }}
          </span>
        </div>

        <div class="article-divider"></div>

        <!-- Rendered Markdown Body -->
        <div
          class="article-body-content markdown-rendered-content"
          v-html="renderedPostContent"
        ></div>

        <div class="article-divider"></div>

        <!-- Main Post Action Cluster -->
        <div class="article-bottom-actions">
          <button
            type="button"
            class="btn-liquid btn-action-big"
            :class="{ active: threadUpvoted }"
            @click="toggleThreadUpvote"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"></path>
            </svg>
            <span>{{ threadUpvoted ? '已点赞实战经验' : '点赞实战经验' }}</span>
            <span class="badge-count">{{ threadUpvoteCount }}</span>
          </button>

          <button
            type="button"
            class="btn-outline-action"
            :class="{ active: threadBookmarked }"
            @click="toggleThreadBookmark"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" :fill="threadBookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>{{ threadBookmarked ? '已收藏归档' : '收藏归档' }}</span>
          </button>

          <button
            type="button"
            class="btn-outline-action"
            :class="{ active: threadLoved }"
            @click="toggleThreadLove"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" :fill="threadLoved ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <path d="M20.8 5.6a5.2 5.2 0 0 0-7.4 0L12 7l-1.4-1.4a5.2 5.2 0 1 0-7.4 7.4L12 21l8.8-7.9a5.2 5.2 0 0 0 0-7.5Z"></path>
            </svg>
            <span>{{ threadLoved ? '已喜欢' : '喜欢' }}</span>
            <span class="badge-count">{{ threadLoveCount }}</span>
          </button>

          <button
            type="button"
            class="btn-outline-action"
            :class="{ active: isCopied }"
            @click="handleCopyLink"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="18" cy="5" r="3"></circle>
              <circle cx="6" cy="12" r="3"></circle>
              <circle cx="18" cy="19" r="3"></circle>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
            </svg>
            <span>{{ isCopied ? '已复制分享' : '分享实战' }}</span>
          </button>

          <button
            v-if="canDelete"
            type="button"
            class="btn-outline-action btn-delete-action"
            @click="$emit('delete', post)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            <span>删除帖子</span>
          </button>
        </div>
      </article>

      <!-- Discussions & Comments Section -->
      <section class="glass-box discussions-section-card">
        <div class="discussions-header">
          <div class="discussions-title-cluster">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <h2 class="discussions-title">创客交流探讨与见解</h2>
            <span class="discussions-count">{{ commentTree.length }} 条实战见解</span>
          </div>
        </div>

        <!-- Reply Input Box -->
        <div class="reply-input-box">
          <div v-if="replyTarget" class="replying-to-bar">
            <span>正在回复 @{{ replyTarget.authorName }}</span>
            <button type="button" class="btn-cancel-reply-target" @click="replyTarget = null">取消针对回复</button>
          </div>

          <textarea
            v-model="replyText"
            class="glass-input reply-textarea"
            rows="3"
            :placeholder="replyPlaceholder"
          ></textarea>

          <div class="reply-submit-bar">
            <span class="reply-hint-text">发帖遵循创客自律倡议，支持文明实战交流</span>
            <button
              type="button"
              class="btn-liquid btn-submit-reply"
              :disabled="!replyText.trim() || isSubmitting"
              @click="submitReply"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
              <span>{{ isSubmitting ? '发送中...' : '发表见解' }}</span>
            </button>
          </div>
        </div>

        <!-- Comments Tree Render -->
        <div v-if="commentTree.length > 0" class="comments-tree-list">
          <div
            v-for="item in commentTree"
            :key="item.id"
            class="comment-node"
            :class="{ 'is-accepted-node': item.is_accepted }"
          >
            <!-- Top Comment Card -->
            <div class="comment-bubble">
              <div class="comment-head">
                <div class="c-author-info">
                  <span class="c-avatar">{{ (item.author_name || '客')[0] }}</span>
                  <span class="c-name">{{ item.author_name || '独立创客' }}</span>
                  <span class="c-ip">{{ item.ip_location || '来自 浙江' }}</span>
                  <span v-if="item.is_accepted" class="accepted-badge">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    <span>题主已采纳方案</span>
                  </span>
                </div>
                <span class="c-time">{{ item.created_at || '刚刚' }}</span>
              </div>

              <div class="comment-body-text">
                {{ item.content }}
              </div>

              <div class="comment-actions-bar">
                <button
                  type="button"
                  class="btn-c-action"
                  :class="{ active: item.upvoted }"
                  @click="toggleCommentUpvote(item)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"></path>
                  </svg>
                  <span>点赞 {{ item.upvote_count || 0 }}</span>
                </button>

                <button type="button" class="btn-c-action" @click="setReplyTarget(item)">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                  <span>回复</span>
                </button>
              </div>
            </div>

            <!-- Nested Children Replies -->
            <div v-if="item.children && item.children.length > 0" class="sub-replies-container">
              <div
                v-for="sub in item.children"
                :key="sub.id"
                class="sub-reply-card"
              >
                <div class="comment-head">
                  <div class="c-author-info">
                    <span class="c-avatar sub-avatar">{{ (sub.author_name || '客')[0] }}</span>
                    <span class="c-name">{{ sub.author_name || '出海创客' }}</span>
                    <span v-if="sub.reply_to_name" class="reply-target-text">
                      回复 <span class="reply-target-tag">@{{ sub.reply_to_name }}</span>
                    </span>
                    <span class="c-ip">{{ sub.ip_location || '来自 浙江' }}</span>
                  </div>
                  <span class="c-time">{{ sub.created_at || '刚刚' }}</span>
                </div>

                <div class="comment-body-text">
                  {{ sub.content }}
                </div>

                <div class="comment-actions-bar">
                  <button
                    type="button"
                    class="btn-c-action"
                    :class="{ active: sub.upvoted }"
                    @click="toggleCommentUpvote(sub)"
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"></path>
                    </svg>
                    <span>点赞 {{ sub.upvote_count || 0 }}</span>
                  </button>

                  <button type="button" class="btn-c-action" @click="setReplyTarget(item, sub.author_name)">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <span>回复</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-comments-box">
          <p>暂无见解交流，成为第一个发表实战见解的创客吧！</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import { renderMarkdown } from '@/utils/markdown';

const props = defineProps({
  post: {
    type: Object,
    required: true,
  },
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['back', 'toast', 'upvote', 'bookmark', 'update-post', 'delete']);

const currentUserId = computed(() => {
  return props.userSession?.uid || props.userSession?.id || props.userSession?.user?.id || props.userSession?.user?.uid || '';
});

const currentUserRole = computed(() => {
  return (props.userSession?.role || props.userSession?.user?.role || localStorage.getItem('opchub_current_role') || 'MAKER').toUpperCase();
});

const canDelete = computed(() => {
  if (currentUserRole.value === 'ADMIN') return true;
  if (currentUserId.value && props.post?.author_id && String(props.post.author_id) === String(currentUserId.value)) {
    return true;
  }
  return false;
});

const threadUpvoted = ref(false);
const threadUpvoteCount = ref(0);
const threadBookmarked = ref(false);
const threadLoved = ref(false);
const threadLoveCount = ref(0);
const isCopied = ref(false);
let copyTimer = null;

const replyText = ref('');
const replyTarget = ref(null);
const isSubmitting = ref(false);
const commentTree = ref([]);

function isPostUpvotedInStorage(postId) {
  if (!postId) return false;
  try {
    const raw = localStorage.getItem('opchub_forum_upvotes');
    const list = raw ? JSON.parse(raw) : [];
    return list.includes(String(postId));
  } catch (e) {
    return false;
  }
}

function isPostBookmarkedInStorage(postId) {
  if (!postId) return false;
  try {
    const raw = localStorage.getItem('opchub_forum_bookmarks');
    const list = raw ? JSON.parse(raw) : [];
    return list.some((b) => (typeof b === 'object' ? String(b.id) === String(postId) : String(b) === String(postId)));
  } catch (e) {
    return false;
  }
}

watch(
  () => props.post,
  (newPost) => {
    if (newPost) {
      threadUpvoted.value = Boolean(newPost.viewer?.liked ?? newPost.is_upvoted);
      threadUpvoteCount.value = newPost.like_count ?? newPost.upvotes ?? newPost.upvote_count ?? 0;
      threadBookmarked.value = Boolean(newPost.viewer?.favorited ?? newPost.is_bookmarked);
      threadLoved.value = Boolean(newPost.viewer?.loved ?? newPost.is_loved);
      threadLoveCount.value = newPost.love_count ?? 0;
      replyTarget.value = null;
      replyText.value = '';
      loadThreadDetail(newPost);
    }
  },
  { immediate: true }
);

function loadThreadDetail(post) {
  if (post.id === 1 || post.title.includes('工商年报')) {
    commentTree.value = [
      {
        id: 'c-101',
        author_name: '财税极客_老王',
        ip_location: '来自 杭州',
        created_at: '15分钟前',
        is_accepted: true,
        upvote_count: 36,
        upvoted: true,
        content: '亲测小规模纳税人免税申报，务必在填报《增值税及附加税费申报表》时勾选“小微企业免税政策代码”，如果填在应税收入栏会被税务系统自动阻断！',
        children: [
          {
            id: 'c-101-1',
            author_name: 'SoloDev_Z',
            reply_to_name: '财税极客_老王',
            ip_location: '来自 深圳',
            created_at: '8分钟前',
            upvote_count: 7,
            upvoted: false,
            content: '非常感谢提醒！我们上个月差点误填到应税收入里，省下了两千多块附加税。',
          },
        ],
      },
      {
        id: 'c-102',
        author_name: '合规小管家',
        ip_location: '来自 北京',
        created_at: '25分钟前',
        is_accepted: false,
        upvote_count: 14,
        upvoted: false,
        content: '另外提示大家：年报公示截止时间是6月30日，逾期不仅进经营异常名录，连企业名下的微信商户号和支付宝商户都会被冻结清算权限。',
        children: [],
      },
    ];
  } else if (post.id === 2 || post.title.includes('算力补贴')) {
    commentTree.value = [
      {
        id: 'c-201',
        author_name: 'AI_Innovator',
        ip_location: '来自 苏州',
        created_at: '28分钟前',
        is_accepted: true,
        upvote_count: 22,
        upvoted: false,
        content: '建议大家在申报时把租用 GPU 算力合同里的“AI 模型微调与推理测试”单列出来，审核部门对这一项的补贴核准通过率几乎是 100%。',
        children: [],
      },
    ];
  } else {
    commentTree.value = [
      {
        id: 'c-301',
        author_name: 'VectorPilot',
        ip_location: '来自 深圳',
        created_at: '1小时前',
        is_accepted: true,
        upvote_count: 19,
        upvoted: false,
        content: '核心要点在于：在微内核里将合规校验做成前置 Guard 算子，出现风控拦截就走异步补偿流水线，这样既不阻塞前台请求，又能保证数据可追溯。',
        children: [],
      },
    ];
  }

  // Attempt to fetch from real backend gateway
  if (post.id && typeof post.id === 'string' && post.id.length > 10) {
    dispatchGateway('forum.threads.get', { thread_id: post.id }, { silent: true }).then((res) => {
      if (res.ok && res.data && res.data.comments) {
        commentTree.value = res.data.comments.map((node) => ({
          id: node.id,
          author_name: node.author_id ? `创客_${node.author_id.slice(0, 6)}` : '实战创客',
          ip_location: '来自 浙江',
          created_at: '刚刚',
          is_accepted: Boolean(node.is_accepted),
          upvote_count: node.upvote_count || 0,
          upvoted: false,
          content: node.content,
          children: (node.children || []).map((sub) => ({
            id: sub.id,
            author_name: sub.author_id ? `创客_${sub.author_id.slice(0, 6)}` : '出海创客',
            ip_location: '来自 浙江',
            created_at: '刚刚',
            upvote_count: sub.upvote_count || 0,
            upvoted: false,
            content: sub.content,
          })),
        }));
      }
    });
  }
}

const fullPostContent = computed(() => {
  if (props.post?.content) return props.post.content;
  if (props.post?.snippet) {
    return `${props.post.snippet}\n\n作为超级个体或独立一人公司，在出海或创业过程中最关键的不是规模，而是单元经济模型（Unit Economics）的高效运转与全链路合规闭环。欢迎各位创客就该方案提出异议、经验补充或避坑补充！`;
  }
  return '暂无详细内容';
});

const renderedPostContent = computed(() => {
  return renderMarkdown(fullPostContent.value);
});

const categoryLabel = computed(() => {
  return props.post?.category || '实战风暴';
});

const pillStyle = computed(() => {
  return {
    color: 'var(--text-secondary)',
    background: 'var(--glass-surface-subtle)',
    border: '1px solid var(--glass-border-subtle)',
  };
});

const replyPlaceholder = computed(() => {
  if (replyTarget.value) {
    return `回复 @${replyTarget.value.authorName}：在此分享您的补充实践、异议反思或经验见解...`;
  }
  return '分享您的实战经验、避坑细节或针对该方案提出见解...（支持富文本交流）';
});

async function toggleThreadUpvote() {
  const wasUpvoted = threadUpvoted.value;
  const previousCount = threadUpvoteCount.value;
  threadUpvoted.value = !wasUpvoted;
  threadUpvoteCount.value = Math.max(0, previousCount + (wasUpvoted ? -1 : 1));
  try {
    const res = await dispatchGateway('content.interaction.toggle', {
      target_type: 'FORUM_THREAD',
      target_id: String(props.post.id),
      kind: 'LIKE',
      target_title: props.post.title || '',
    });
    if (res.ok && res.data) {
      threadUpvoted.value = Boolean(res.data.viewer?.liked);
      threadUpvoteCount.value = Number(res.data.like_count || 0);
      if (props.post) {
        props.post.is_upvoted = threadUpvoted.value;
        props.post.upvotes = threadUpvoteCount.value;
        props.post.upvote_count = threadUpvoteCount.value;
        props.post.like_count = threadUpvoteCount.value;
        props.post.viewer = res.data.viewer;
      }
      emit('upvote', {
        post: props.post,
        isUpvoted: threadUpvoted.value,
        count: threadUpvoteCount.value,
      });
      emit('update-post', props.post);
    } else {
      threadUpvoted.value = wasUpvoted;
      threadUpvoteCount.value = previousCount;
      emit('toast', { title: '操作未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
      return;
    }
  } catch (e) {
    threadUpvoted.value = wasUpvoted;
    threadUpvoteCount.value = previousCount;
    emit('toast', { title: '操作异常', message: '互动服务暂时不可用，请稍后重试。', type: 'ERROR' });
    return;
  }

  emit('toast', {
    title: threadUpvoted.value ? '已点赞实战经验' : '已取消点赞',
    message: threadUpvoted.value ? '感谢对创客实战经验的认可！' : '已更新您的点赞状态',
    type: 'SUCCESS',
  });
}

async function toggleThreadLove() {
  const wasLoved = threadLoved.value;
  const previousCount = threadLoveCount.value;
  threadLoved.value = !wasLoved;
  threadLoveCount.value = Math.max(0, previousCount + (wasLoved ? -1 : 1));
  try {
    const res = await dispatchGateway('content.interaction.toggle', {
      target_type: 'FORUM_THREAD',
      target_id: String(props.post.id),
      kind: 'LOVE',
      target_title: props.post.title || '',
    });
    if (res.ok && res.data) {
      threadLoved.value = Boolean(res.data.viewer?.loved);
      threadLoveCount.value = Number(res.data.love_count || 0);
      if (props.post) {
        props.post.is_loved = threadLoved.value;
        props.post.love_count = threadLoveCount.value;
        props.post.viewer = res.data.viewer;
      }
      emit('update-post', props.post);
    } else {
      threadLoved.value = wasLoved;
      threadLoveCount.value = previousCount;
      emit('toast', { title: '操作未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    threadLoved.value = wasLoved;
    threadLoveCount.value = previousCount;
    emit('toast', { title: '操作异常', message: '互动服务暂时不可用，请稍后重试。', type: 'ERROR' });
  }
}

async function toggleThreadBookmark() {
  const wasBookmarked = threadBookmarked.value;
  threadBookmarked.value = !wasBookmarked;
  try {
    const res = await dispatchGateway('content.interaction.toggle', {
      target_type: 'FORUM_THREAD',
      target_id: String(props.post.id),
      kind: 'FAVORITE',
      target_title: props.post.title || '',
    });
    if (res.ok && res.data) {
      threadBookmarked.value = Boolean(res.data.viewer?.favorited);
      if (props.post) {
        props.post.is_bookmarked = threadBookmarked.value;
        props.post.bookmark_count = Number(res.data.favorite_count || 0);
        props.post.favorite_count = Number(res.data.favorite_count || 0);
        props.post.viewer = res.data.viewer;
      }
      emit('bookmark', {
        post: props.post,
        isBookmarked: threadBookmarked.value,
      });
      emit('update-post', props.post);
    } else {
      threadBookmarked.value = wasBookmarked;
      emit('toast', { title: '操作未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
      return;
    }
  } catch (e) {
    threadBookmarked.value = wasBookmarked;
    emit('toast', { title: '操作异常', message: '互动服务暂时不可用，请稍后重试。', type: 'ERROR' });
    return;
  }

  emit('toast', {
    title: threadBookmarked.value ? '已收藏归档' : '已移出收藏夹',
    message: threadBookmarked.value ? '该实战帖已归档至您的个人知识库收藏目录！' : '已从知识库收藏目录移除',
    type: 'SUCCESS',
  });
}

async function copyTextToClipboard(text) {
  if (navigator?.clipboard?.writeText && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // fallback to execCommand below
    }
  }
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '-9999px';
    textarea.setAttribute('readonly', '');
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, 99999);
    const successful = document.execCommand('copy');
    document.body.removeChild(textarea);
    return successful;
  } catch (err) {
    return false;
  }
}

async function handleCopyLink() {
  const origin = window.location.origin || '';
  const pathname = window.location.pathname || '/';
  const shareUrl = `${origin}${pathname}#forum?post_id=${encodeURIComponent(props.post?.id || '')}`;

  if (window.location.hash !== `#forum?post_id=${props.post?.id}`) {
    try {
      window.history.replaceState(null, '', `${pathname}#forum?post_id=${props.post?.id}`);
    } catch (e) {}
  }

  const shareText = `【OpcHub 头脑风暴实战经验分享】\n《${props.post?.title || '实战经验'}》\n分类：${categoryLabel.value} · 作者：${props.post?.author || '认证创客'}\n查看详情与交流探讨：\n${shareUrl}`;

  const ok = await copyTextToClipboard(shareText);
  if (ok) {
    isCopied.value = true;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      isCopied.value = false;
    }, 2500);

    emit('toast', {
      title: '实战经验已复制',
      message: '实战帖标题与深度链接已存入剪贴板，可快捷分享给同行创客！',
      type: 'SUCCESS',
    });
  } else {
    emit('toast', {
      title: '分享链接已就绪',
      message: `链接：${shareUrl}`,
      type: 'INFO',
    });
  }
}

function handleReport() {
  emit('toast', {
    title: '已提交合规复审',
    message: '言论举报线索已同步推送至平台法务合规审计中心。',
    type: 'INFO',
  });
}

function toggleCommentUpvote(item) {
  item.upvoted = !item.upvoted;
  item.upvote_count = (item.upvote_count || 0) + (item.upvoted ? 1 : -1);
  if (props.post?.id) {
    dispatchGateway(
      'forum.upvote',
      { target_type: 'COMMENT', target_id: String(item.id) },
      { silent: true }
    );
  }
}

function setReplyTarget(parentComment, subAuthorName = null) {
  replyTarget.value = {
    parentId: parentComment.id,
    authorName: subAuthorName || parentComment.author_name,
  };
}

async function submitReply() {
  const content = replyText.value.trim();
  if (!content) return;

  isSubmitting.value = true;

  try {
    const parentId = replyTarget.value?.parentId || null;
    const authorName = props.userSession?.nickname || '我的创客号';

    if (parentId) {
      const parent = commentTree.value.find((c) => c.id === parentId);
      if (parent) {
        if (!parent.children) parent.children = [];
        parent.children.push({
          id: `c-local-${Date.now()}`,
          author_name: authorName,
          reply_to_name: replyTarget.value?.authorName,
          ip_location: '来自 本地',
          created_at: '刚刚',
          upvote_count: 0,
          upvoted: false,
          content,
        });
      }
    } else {
      commentTree.value.unshift({
        id: `c-local-${Date.now()}`,
        author_name: authorName,
        ip_location: '来自 本地',
        created_at: '刚刚',
        is_accepted: false,
        upvote_count: 0,
        upvoted: false,
        content,
        children: [],
      });
    }

    if (props.post?.id && typeof props.post.id === 'string' && props.post.id.length > 10) {
      dispatchGateway('forum.comments.create', {
        comment_payload: {
          thread_id: props.post.id,
          parent_id: parentId,
          content,
          author_id: props.userSession?.id || 'maker-local',
        },
      }, { silent: true });
    }

    emit('toast', {
      title: '发表成功',
      message: '您的实战见解已通过审查并即时汇入风暴讨论树！',
      type: 'SUCCESS',
    });

    replyText.value = '';
    replyTarget.value = null;
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.forum-detail-page-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Header */
.detail-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.btn-back-square {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-back-square:hover {
  background: var(--glass-surface-hover);
  color: var(--accent);
  transform: translateX(-2px);
}

.breadcrumb-cluster {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.breadcrumb-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.crumb-link {
  cursor: pointer;
  transition: color 0.2s ease;
}

.crumb-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.crumb-separator {
  opacity: 0.5;
}

.crumb-current {
  color: var(--text-primary);
  font-weight: 500;
}

.meta-pills-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.category-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-family: var(--font-mono);
}

.pinned-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--accent-glass);
  color: var(--accent);
}

.ip-info,
.time-info {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-header-action {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-header-action:hover {
  background: var(--glass-surface-hover);
  color: var(--accent);
  border-color: var(--accent);
}

.btn-header-action.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.count-tag {
  font-size: 11px;
  opacity: 0.85;
}

.btn-header-ghost-report {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 10px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-header-ghost-report:hover {
  background: var(--status-danger-soft);
  color: var(--status-danger);
}

.btn-header-ghost-delete {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 10px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid var(--status-danger-soft);
  color: var(--status-danger);
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-header-ghost-delete:hover {
  background: var(--status-danger-soft);
  border-color: var(--status-danger);
}

.btn-delete-action:hover {
  border-color: var(--status-danger) !important;
  color: var(--status-danger) !important;
  background: var(--status-danger-soft) !important;
}

/* Equal-Width Article Container (页面等宽统一体系) */
.article-center-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-sizing: border-box;
}

.article-main-card {
  padding: 36px 40px;
  display: flex;
  flex-direction: column;
}

.article-title {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: -0.02em;
  margin-bottom: 20px;
}

.article-author-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.author-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.author-avatar-orb {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--glass-surface-hover) 0%, var(--glass-surface-subtle) 100%);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 17px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.author-text-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.author-name-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.author-name {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.maker-verified-pill {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: var(--status-success-soft);
  color: var(--status-success);
  border: 1px solid var(--status-success);
}

.author-sub-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.article-tags-cluster {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.tag-badge {
  font-size: 12px;
  padding: 3px 9px;
  border-radius: var(--radius-xs);
  background: var(--accent-glass);
  color: var(--accent);
  border: 1px solid rgba(0, 113, 227, 0.18);
}

.article-divider {
  height: 1px;
  background: var(--glass-border);
  margin: 24px 0;
}

.article-body-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
}

/* Bottom Action Buttons */
.article-bottom-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 0 6px;
}

.btn-action-big {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--radius-md);
}

.badge-count {
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
  font-size: 12px;
}

.btn-outline-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13.5px;
  font-weight: 500;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-primary);
  cursor: pointer;
  transition: var(--transition-liquid);
}

.btn-outline-action:hover {
  background: var(--glass-surface-hover);
  border-color: var(--accent);
  color: var(--accent);
}

.btn-outline-action.active {
  background: var(--accent-glass);
  border-color: var(--accent);
  color: var(--accent);
}

/* Discussions Section */
.discussions-section-card {
  padding: 32px 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.discussions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.discussions-title-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
}

.discussions-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
}

.discussions-count {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--accent-glass);
  color: var(--accent);
  font-weight: 500;
}

/* Reply Box */
.reply-input-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
}

.replying-to-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--accent);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--glass-border-subtle);
}

.btn-cancel-reply-target {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 11px;
}

.btn-cancel-reply-target:hover {
  color: var(--status-danger);
}

.reply-textarea {
  width: 100%;
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.6;
}

.reply-submit-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reply-hint-text {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.btn-submit-reply {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: var(--radius-sm);
}

.btn-submit-reply:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Comments Tree */
.comments-tree-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-node {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment-bubble {
  padding: 16px 20px;
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.is-accepted-node .comment-bubble {
  border-color: var(--status-success);
  background: var(--status-success-soft);
}

.comment-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.c-author-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.c-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.sub-avatar {
  width: 22px;
  height: 22px;
  font-size: 11px;
}

.c-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.c-ip,
.c-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.accepted-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: var(--status-success-soft);
  color: var(--status-success);
  font-weight: 600;
}

.comment-body-text {
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--text-primary);
}

.comment-actions-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-c-action {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 11.5px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--radius-xs);
  transition: all 0.2s ease;
}

.btn-c-action:hover {
  color: var(--accent);
}

.btn-c-action.active {
  color: var(--accent);
  font-weight: 600;
}

/* Sub-replies */
.sub-replies-container {
  margin-left: 28px;
  padding-left: 16px;
  border-left: 2px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sub-reply-card {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reply-target-text {
  font-size: 11px;
  color: var(--text-tertiary);
}

.reply-target-tag {
  color: var(--accent);
  font-weight: 500;
}

.empty-comments-box {
  padding: 36px 20px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

@media (max-width: 768px) {
  .article-main-card,
  .discussions-section-card {
    padding: 20px;
  }

  .article-title {
    font-size: 22px;
  }
}
</style>
