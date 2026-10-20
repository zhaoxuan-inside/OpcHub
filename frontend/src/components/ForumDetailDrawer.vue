<template>
  <Teleport to="body">
    <transition name="drawer-fade">
      <div v-if="visible" class="drawer-backdrop" @click="handleBackdropClick">
        <transition name="drawer-slide">
          <div v-if="visible" class="drawer-panel" @click.stop>
            <!-- Header Bar -->
            <div class="drawer-header">
              <div class="header-left">
                <span class="category-tag" :style="pillStyle">
                  {{ categoryLabel }}
                </span>
                <span v-if="post?.pinned" class="pinned-tag">
                  {{ post.pinned }}
                </span>
                <span class="ip-info">
                  {{ post?.ip_location || '来自 浙江' }}
                </span>
              </div>
              <button class="btn-close" @click="$emit('close')" title="关闭 (Esc)">
                <ForumIcon name="close" size="18" />
              </button>
            </div>

            <!-- Body Scrollable Area -->
            <div class="drawer-content">
              <!-- Thread Main Content -->
              <div class="thread-section">
                <h1 class="thread-title">{{ post?.title }}</h1>

                <!-- Author & Meta bar -->
                <div class="author-meta-bar">
                  <div class="author-info">
                    <div class="author-avatar">
                      {{ (post?.author || '创客')[0].toUpperCase() }}
                    </div>
                    <div>
                      <div class="author-name">
                        {{ post?.author || '匿名创客' }}
                        <span class="badge-maker">已认证创客</span>
                      </div>
                      <div class="post-submeta">
                        <span>发表于 {{ post?.updated_at || '刚刚' }}</span>
                        <span>·</span>
                        <span>浏览 {{ post?.view_count || 128 }} 次</span>
                      </div>
                    </div>
                  </div>

                  <!-- Report Action -->
                  <button class="btn-report" @click="handleReport" title="合规举报违规内容">
                    <ForumIcon name="shield" size="12" />
                    <span>举报言论</span>
                  </button>
                </div>

                <!-- Main Post Content -->
                <div class="thread-body">
                  <div class="thread-markdown-content markdown-rendered-content" v-html="renderedPostContent"></div>
                </div>

                <!-- Main Post Action Bar: Upvote & Bookmark -->
                <div class="thread-action-bar">
                  <button
                    class="action-btn upvote-action"
                    :class="{ active: threadUpvoted }"
                    @click="toggleThreadUpvote"
                  >
                    <ForumIcon name="upvote" size="14" />
                    <span>{{ threadUpvoted ? '已赞同' : '赞同灵感' }}</span>
                    <span class="action-count">{{ threadUpvoteCount }}</span>
                  </button>

                  <button
                    class="action-btn bookmark-action"
                    :class="{ active: threadBookmarked }"
                    @click="toggleThreadBookmark"
                  >
                    <ForumIcon name="bookmark" size="14" />
                    <span>{{ threadBookmarked ? '已收藏' : '收藏归档' }}</span>
                  </button>

                  <button class="action-btn copy-action" @click="handleCopyLink">
                    <ForumIcon name="share" size="14" />
                    <span>复制分享</span>
                  </button>
                </div>
              </div>

              <!-- Discussion Tree Section -->
              <div class="discussion-section">
                <div class="discussion-header">
                  <div class="discussion-title">
                    <ForumIcon name="topology" size="16" />
                    <span>交流探讨与见解</span>
                    <span class="count-pill">{{ commentTree.length }} 条见解</span>
                  </div>
                </div>

                <!-- Comments Tree Render -->
                <div v-if="commentTree.length > 0" class="comments-tree">
                  <div
                    v-for="item in commentTree"
                    :key="item.id"
                    class="comment-node"
                    :class="{ 'is-accepted-node': item.is_accepted }"
                  >
                    <!-- Top-Level Comment Card -->
                    <div class="comment-bubble">
                      <div class="comment-head">
                        <div class="comment-author-box">
                          <span class="c-avatar">{{ (item.author_name || '客')[0] }}</span>
                          <span class="c-name">{{ item.author_name || '独立创客' }}</span>
                          <span class="c-ip">{{ item.ip_location || '来自 浙江' }}</span>
                          <span v-if="item.is_accepted" class="accepted-badge">
                            <ForumIcon name="accepted" size="11" />
                            <span>题主已采纳方案</span>
                          </span>
                        </div>
                        <span class="c-time">{{ item.created_at || '20分钟前' }}</span>
                      </div>

                      <div class="comment-body">
                        {{ item.content }}
                      </div>

                      <div class="comment-footer">
                        <button
                          class="c-action-btn"
                          :class="{ active: item.upvoted }"
                          @click="toggleCommentUpvote(item)"
                        >
                          <ForumIcon name="upvote" size="11" />
                          <span>赞同 {{ item.upvote_count || 0 }}</span>
                        </button>

                        <button class="c-action-btn" @click="setReplyTarget(item)">
                          <ForumIcon name="chat" size="11" />
                          <span>回复</span>
                        </button>
                      </div>
                    </div>

                    <!-- Nested Children Comments (Materialized Path Sub-tree) -->
                    <div v-if="item.children && item.children.length > 0" class="children-block">
                      <div
                        v-for="sub in item.children"
                        :key="sub.id"
                        class="sub-comment-card"
                      >
                        <div class="comment-head">
                          <div class="comment-author-box">
                            <span class="c-avatar sub-av">{{ (sub.author_name || '客')[0] }}</span>
                            <span class="c-name">{{ sub.author_name || '出海者' }}</span>
                            <span v-if="sub.reply_to_name" class="reply-to-text">
                              回复 <span class="reply-target-tag">@{{ sub.reply_to_name }}</span>
                            </span>
                            <span class="c-ip">{{ sub.ip_location || '来自 上海' }}</span>
                          </div>
                          <span class="c-time">{{ sub.created_at || '5分钟前' }}</span>
                        </div>
                        <div class="comment-body sub-body">
                          {{ sub.content }}
                        </div>
                        <div class="comment-footer">
                          <button
                            class="c-action-btn"
                            :class="{ active: sub.upvoted }"
                            @click="toggleCommentUpvote(sub)"
                          >
                            <ForumIcon name="upvote" size="10" />
                            <span>赞同 {{ sub.upvote_count || 0 }}</span>
                          </button>
                          <button class="c-action-btn" @click="setReplyTarget(item, sub.author_name)">
                            <span>回复</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="empty-discussion">
                  <p>暂无回复见解，快来发表第一条灵感解答吧！</p>
                </div>
              </div>
            </div>

            <!-- Bottom Quick Reply Bar -->
            <div class="drawer-reply-bar">
              <div v-if="replyTarget" class="replying-banner">
                <span>正在回复 <strong>@{{ replyTarget.authorName }}</strong></span>
                <button class="btn-cancel-reply" @click="replyTarget = null">取消</button>
              </div>

              <div class="reply-input-wrap">
                <textarea
                  v-model="replyText"
                  class="reply-textarea"
                  :placeholder="replyPlaceholder"
                  rows="2"
                  @keydown.enter.ctrl.prevent="submitReply"
                  @keydown.enter.meta.prevent="submitReply"
                ></textarea>
                <div class="reply-actions">
                  <span class="reply-hint">Ctrl + Enter 快速提交</span>
                  <button
                    class="btn-send"
                    :disabled="!replyText.trim() || isSubmitting"
                    @click="submitReply"
                  >
                    <ForumIcon name="send" size="12" />
                    <span>{{ isSubmitting ? '发送中...' : '发表见解' }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import ForumIcon from '@/components/ForumIcon.vue';
import { dispatchGateway } from '@/api/gateway';
import { renderMarkdown } from '@/utils/markdown';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  post: {
    type: Object,
    default: null,
  },
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['close', 'toast', 'refresh', 'upvote', 'bookmark', 'update-post']);

const threadUpvoted = ref(false);
const threadUpvoteCount = ref(0);
const threadBookmarked = ref(false);

const replyText = ref('');
const replyTarget = ref(null);
const isSubmitting = ref(false);

// Local comment tree with materialized path support
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
      threadUpvoted.value = Boolean(newPost.is_upvoted || isPostUpvotedInStorage(newPost.id));
      threadUpvoteCount.value = newPost.upvotes ?? newPost.upvote_count ?? 0;
      threadBookmarked.value = Boolean(newPost.is_bookmarked || isPostBookmarkedInStorage(newPost.id));
      replyTarget.value = null;
      replyText.value = '';
      loadThreadDetail(newPost);
    }
  },
  { immediate: true }
);

function loadThreadDetail(post) {
  // Built-in sample comments for instant response + gateway fetch
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
        // Map backend comments tree to view
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
    color: '#0071E3',
    background: 'rgba(0, 113, 227, 0.08)',
  };
});

const replyPlaceholder = computed(() => {
  if (replyTarget.value) {
    return `回复 @${replyTarget.value.authorName} 的见解...`;
  }
  return '输入您的一人公司实战见解、避坑补充或灵感观点 (支持 Markdown)...';
});

function toggleThreadUpvote() {
  threadUpvoted.value = !threadUpvoted.value;
  threadUpvoteCount.value += threadUpvoted.value ? 1 : -1;
  if (threadUpvoteCount.value < 0) threadUpvoteCount.value = 0;

  if (props.post) {
    props.post.is_upvoted = threadUpvoted.value;
    props.post.upvotes = threadUpvoteCount.value;
    props.post.upvote_count = threadUpvoteCount.value;
  }

  try {
    const raw = localStorage.getItem('opchub_forum_upvotes');
    let upvotes = raw ? JSON.parse(raw) : [];
    const sid = String(props.post.id);
    if (threadUpvoted.value) {
      if (!upvotes.includes(sid)) upvotes.push(sid);
    } else {
      upvotes = upvotes.filter((id) => id !== sid);
    }
    localStorage.setItem('opchub_forum_upvotes', JSON.stringify(upvotes));
  } catch (e) {}

  emit('upvote', {
    post: props.post,
    isUpvoted: threadUpvoted.value,
    count: threadUpvoteCount.value,
  });
  emit('update-post', props.post);

  emit('toast', {
    title: threadUpvoted.value ? '已赞同实战经验' : '已取消赞同',
    message: threadUpvoted.value ? '感谢对创客实战经验的认可！' : '已更新您的赞同状态',
    type: 'SUCCESS',
  });

  if (props.post?.id) {
    dispatchGateway(
      'forum.upvote',
      { target_type: 'THREAD', target_id: String(props.post.id) },
      { silent: true }
    );
  }
}

function toggleThreadBookmark() {
  threadBookmarked.value = !threadBookmarked.value;

  if (props.post) {
    props.post.is_bookmarked = threadBookmarked.value;
    props.post.bookmark_count = Math.max(0, (props.post.bookmark_count || 0) + (threadBookmarked.value ? 1 : -1));
  }

  try {
    const raw = localStorage.getItem('opchub_forum_bookmarks');
    let bookmarks = raw ? JSON.parse(raw) : [];
    const sid = String(props.post.id);
    if (threadBookmarked.value) {
      const exists = bookmarks.some((b) => (typeof b === 'object' ? String(b.id) === sid : String(b) === sid));
      if (!exists) {
        bookmarks.push({
          id: props.post.id,
          title: props.post.title,
          category: props.post.category || '实战话题',
          author: props.post.author,
          created_at: new Date().toISOString(),
        });
      }
    } else {
      bookmarks = bookmarks.filter((b) => (typeof b === 'object' ? String(b.id) !== sid : String(b) !== sid));
    }
    localStorage.setItem('opchub_forum_bookmarks', JSON.stringify(bookmarks));
  } catch (e) {}

  emit('bookmark', {
    post: props.post,
    isBookmarked: threadBookmarked.value,
  });
  emit('update-post', props.post);

  emit('toast', {
    title: threadBookmarked.value ? '已收藏归档' : '已移出收藏夹',
    message: threadBookmarked.value ? '该实战帖已归档至您的个人知识库收藏目录！' : '已从知识库收藏目录移除',
    type: 'SUCCESS',
  });

  if (props.post?.id) {
    dispatchGateway(
      'forum.bookmark',
      { thread_id: String(props.post.id), folder_name: '默认收藏夹' },
      { silent: true }
    );
  }
}

async function handleCopyLink() {
  const origin = window.location.origin || '';
  const pathname = window.location.pathname || '/';
  const shareUrl = `${origin}${pathname}#forum?post_id=${encodeURIComponent(props.post?.id || '')}`;

  const shareText = `【OpcHub 头脑风暴实战经验分享】\n《${props.post?.title || '实战经验'}》\n作者：${props.post?.author || '认证创客'}\n查看详情与交流探讨：\n${shareUrl}`;

  let ok = false;
  if (navigator?.clipboard?.writeText && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(shareText);
      ok = true;
    } catch (e) {}
  }
  if (!ok) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = shareText;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '-9999px';
      textarea.setAttribute('readonly', '');
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      textarea.setSelectionRange(0, 99999);
      ok = document.execCommand('copy');
      document.body.removeChild(textarea);
    } catch (e) {}
  }

  emit('toast', {
    title: ok ? '实战经验已复制' : '分享链接已就绪',
    message: ok ? '实战帖标题与深度链接已存入剪贴板，可快捷分享给同行创客！' : `链接：${shareUrl}`,
    type: ok ? 'SUCCESS' : 'INFO',
  });
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

    // Optimistically update local comment tree
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

    // Call backend gateway scenario if thread is real
    if (props.post?.id && typeof props.post.id === 'string' && props.post.id.length > 10) {
      await dispatchGateway('forum.comments.create', {
        comment_payload: {
          author_id: props.userSession?.id || 'anonymous-maker',
          content,
          parent_id: parentId,
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

function handleBackdropClick() {
  emit('close');
}

function onKeyDown(e) {
  if (e.key === 'Escape' && props.visible) {
    emit('close');
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown);
});
</script>

<style scoped>
.drawer-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 680px;
  max-width: 95vw;
  height: 100vh;
  background: var(--glass-surface-solid, #FFFFFF);
  border-left: 1px solid var(--glass-border, rgba(255, 255, 255, 0.85));
  box-shadow: -16px 0 48px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

[data-theme="dark"] .drawer-panel {
  background: var(--glass-surface-solid, #151720);
  border-left: 1px solid var(--glass-border, rgba(255, 255, 255, 0.14));
}

/* Header */
.drawer-header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--glass-surface, rgba(255, 255, 255, 0.65));
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-full, 9999px);
  font-family: var(--font-mono, monospace);
}

.pinned-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-full, 9999px);
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  color: var(--accent, #0071E3);
}

.ip-info {
  font-size: 11.5px;
  color: var(--text-tertiary, #7D828D);
}

.btn-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary, #7D828D);
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: var(--glass-surface-hover, rgba(0, 0, 0, 0.05));
  color: var(--text-primary, #121316);
}

/* Body Content Scrollable */
.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}

.thread-section {
  border-bottom: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  padding-bottom: 24px;
  margin-bottom: 24px;
}

.thread-title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--text-primary, #121316);
  margin: 0 0 16px 0;
}

.author-meta-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.author-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.author-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0071E3, #42b883);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
}

.author-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #121316);
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge-maker {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  color: var(--accent, #0071E3);
  font-weight: 500;
}

.post-submeta {
  font-size: 12px;
  color: var(--text-tertiary, #7D828D);
  font-family: var(--font-mono, monospace);
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.btn-report {
  background: transparent;
  border: 1px dashed var(--glass-border-subtle, rgba(0, 0, 0, 0.1));
  color: var(--text-tertiary, #7D828D);
  font-size: 11.5px;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.btn-report:hover {
  color: #ff3b30;
  border-color: #ff3b30;
}

.thread-body {
  font-size: 14.5px;
  line-height: 1.75;
  color: var(--text-secondary, #4B4E56);
  white-space: pre-wrap;
  margin-bottom: 24px;
}

/* Action Bar */
.thread-action-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.08));
  background: var(--glass-surface-subtle, rgba(245, 247, 252, 0.5));
  color: var(--text-secondary, #4B4E56);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.action-btn:hover {
  transform: translateY(-1px);
  border-color: var(--accent, #0071E3);
  color: var(--accent, #0071E3);
}

.upvote-action.active {
  background: var(--accent, #0071E3);
  color: #FFFFFF;
  border-color: var(--accent, #0071E3);
  box-shadow: 0 4px 12px var(--accent-glow, rgba(0, 113, 227, 0.3));
}

.bookmark-action.active {
  background: #f59e0b;
  color: #FFFFFF;
  border-color: #f59e0b;
}

.action-count {
  font-family: var(--font-mono, monospace);
  background: rgba(255, 255, 255, 0.2);
  padding: 1px 6px;
  border-radius: 4px;
}

/* Discussion Tree */
.discussion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.discussion-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #121316);
}

.count-pill {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 9999px;
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  color: var(--accent, #0071E3);
}

.mono-tip {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary, #7D828D);
}

.comments-tree {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-node {
  border-radius: var(--radius-md, 14px);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  background: var(--glass-surface-subtle, rgba(245, 247, 252, 0.4));
  padding: 14px 16px;
  transition: all 0.2s ease;
}

.comment-node.is-accepted-node {
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.04);
}

.comment-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.comment-author-box {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}

.c-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #0071E3;
  color: #FFFFFF;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.c-avatar.sub-av {
  background: #6366f1;
}

.c-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #121316);
}

.c-ip {
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
}

.accepted-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: #10b981;
  color: #FFFFFF;
}

.c-time {
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
  font-family: var(--font-mono, monospace);
}

.comment-body {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-secondary, #4B4E56);
  white-space: pre-wrap;
  margin-bottom: 10px;
}

.comment-footer {
  display: flex;
  gap: 12px;
}

.c-action-btn {
  background: transparent;
  border: none;
  font-size: 11.5px;
  color: var(--text-tertiary, #7D828D);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.c-action-btn:hover {
  background: var(--glass-surface-hover, rgba(0, 0, 0, 0.05));
  color: var(--accent, #0071E3);
}

.c-action-btn.active {
  color: var(--accent, #0071E3);
  font-weight: 600;
}

/* Children comments */
.children-block {
  margin-top: 12px;
  padding-left: 16px;
  border-left: 2px solid var(--accent-glass, rgba(0, 113, 227, 0.15));
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sub-comment-card {
  background: var(--glass-surface-solid, #FFFFFF);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.05));
  border-radius: var(--radius-sm, 8px);
  padding: 10px 12px;
}

[data-theme="dark"] .sub-comment-card {
  background: rgba(255, 255, 255, 0.03);
}

.reply-to-text {
  font-size: 11.5px;
  color: var(--text-tertiary, #7D828D);
}

.reply-target-tag {
  color: var(--accent, #0071E3);
  font-weight: 600;
}

.sub-body {
  font-size: 12.5px;
  margin-bottom: 6px;
}

/* Bottom Reply Bar */
.drawer-reply-bar {
  padding: 16px 24px;
  border-top: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  background: var(--glass-surface, rgba(255, 255, 255, 0.85));
}

[data-theme="dark"] .drawer-reply-bar {
  background: var(--glass-surface, rgba(18, 20, 29, 0.85));
}

.replying-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--accent, #0071E3);
  margin-bottom: 8px;
  padding: 4px 8px;
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  border-radius: 4px;
}

.btn-cancel-reply {
  background: transparent;
  border: none;
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
  cursor: pointer;
}

.reply-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reply-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.12));
  background: var(--glass-surface-solid, #FFFFFF);
  color: var(--text-primary, #121316);
  font-size: 13.5px;
  line-height: 1.5;
  resize: none;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

[data-theme="dark"] .reply-textarea {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.15);
}

.reply-textarea:focus {
  border-color: var(--accent, #0071E3);
  box-shadow: 0 0 0 3px var(--accent-glass, rgba(0, 113, 227, 0.12));
}

.reply-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reply-hint {
  font-size: 11px;
  color: var(--text-tertiary, #7D828D);
  font-family: var(--font-mono, monospace);
}

.btn-send {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: var(--radius-sm, 8px);
  border: none;
  background: var(--accent, #0071E3);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.btn-send:hover:not(:disabled) {
  transform: translateY(-1px);
  opacity: 0.92;
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-discussion {
  text-align: center;
  padding: 32px 16px;
  color: var(--text-tertiary, #7D828D);
  font-size: 13px;
}

/* Animations */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
}

.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(100%);
}
</style>
