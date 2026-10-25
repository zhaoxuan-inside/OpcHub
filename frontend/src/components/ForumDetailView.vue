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
            <span class="time-info">发表于 {{ post?.updated_at || '刚刚' }}</span>
          </div>
        </div>
      </div>

      <!-- Header Right Actions (share / edit / delete — 互动与举报统一在下方互动条) -->
      <div class="header-right-actions">
        <button
          type="button"
          class="btn-header-ghost-action"
          :class="{ active: isCopied }"
          @click="handleCopyLink"
          title="分享实战帖"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="18" cy="5" r="3"></circle>
            <circle cx="6" cy="12" r="3"></circle>
            <circle cx="18" cy="19" r="3"></circle>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
          </svg>
          <span>{{ isCopied ? '已复制' : '分享' }}</span>
        </button>

        <button
          v-if="canEdit"
          type="button"
          class="btn-header-ghost-action"
          @click="openEditPanel"
          title="编辑这篇讨论帖"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
          </svg>
          <span>编辑</span>
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

    <!-- Centered Full-Page Article Container -->
    <div class="article-center-container">
      <article class="glass-box article-main-card">
        <!-- Post Title -->
        <h1 class="article-title">{{ post?.title }}</h1>
        <OfficialBadge v-if="post?.is_official" label="官方" title="官方发布：由平台官方账号发布并认证" />

        <!-- Author Information Bar -->
        <div class="article-author-bar">
          <div class="author-left">
            <div class="author-avatar-orb">
              {{ (post?.author || '创客')[0].toUpperCase() }}
            </div>
            <div class="author-text-meta">
              <div class="author-name-line">
                <span class="author-name">{{ post?.author || '' }}</span>
                <span v-if="post?.author_title" class="maker-verified-pill">{{ post.author_title }}</span>
              </div>
              <div class="author-sub-line">
                <span>浏览 {{ post?.view_count || 0 }} 次</span>
                <span>·</span>
                <span>{{ commentTree.length }} 条探讨见解</span>
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

        <!-- 展示页面免责声明 -->
        <ContentDisclaimer type="forum" />

        <div class="article-divider"></div>

        <!-- Main Post Action Cluster (赞同/反对是唯一投票链路：论坛域 forum.vote) -->
        <div class="article-bottom-actions">
          <div class="zhihu-vote-group vote-group-big">
            <button
              type="button"
              class="btn-zhihu-vote btn-zhihu-upvote"
              :class="{ active: threadUserVote === 'UPVOTE' }"
              @click="handleThreadVote('UPVOTE')"
              title="赞同此议题与实战观点"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 4L3 18h18L12 4z"/>
              </svg>
              <span>赞同 {{ threadUpvoteCount }}</span>
            </button>
            <button
              type="button"
              class="btn-zhihu-vote btn-zhihu-downvote"
              :class="{ active: threadUserVote === 'DOWNVOTE' }"
              @click="handleThreadVote('DOWNVOTE')"
              title="反对 / 不赞同"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 20l9-14H3l9 14z"/>
              </svg>
              <span>反对</span>
            </button>
          </div>

          <button
            type="button"
            class="btn-action-ghost"
            @click="toggleComposer"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            <span>{{ isWritingAnswer ? '收起回答框' : '撰写深度观点' }}</span>
          </button>

          <button
            type="button"
            class="btn-action-ghost"
            :class="{ active: isFollowing }"
            @click="handleToggleFollow"
            title="关注该议题动态"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            <span>{{ isFollowing ? '已关注议题' : '关注议题' }}</span>
          </button>
        </div>

        <!-- Unified Interaction Bar (评分 / 收藏 / 喜欢 / 评论 / 举报) -->
        <div class="detail-interaction-row" @click.stop>
          <ContentInteractionBar
            :target-type="'FORUM_THREAD'"
            :target-id="post?.id"
            :target-title="post?.title || ''"
            :target-snippet="post?.snippet || ''"
            :kinds="['LOVE', 'FAVORITE']"
            :favorite-count="post?.favorite_count ?? post?.bookmark_count ?? 0"
            :love-count="post?.love_count ?? 0"
            :comment-count="post?.comment_count ?? post?.replies ?? 0"
            :rating-avg="post?.rating_avg ?? 0"
            :rating-count="post?.rating_count ?? 0"
            :my-rating="post?.viewer?.rating ?? 0"
            :favorited="post?.viewer ? post.viewer.favorited : Boolean(post?.is_bookmarked)"
            :loved="post?.viewer ? post.viewer.loved : Boolean(post?.is_loved)"
            :commented="post?.viewer ? post.viewer.commented : Boolean(post?.is_commented)"
            :authenticated="Boolean(currentUserId)"
            comment-mode="emit"
            @open-comments="scrollToDiscussions"
            @changed="onInteractionChanged"
            @require-login="$emit('require-login')"
            @toast="$emit('toast', $event)"
          />
        </div>
      </article>

      <!-- Thread Edit Panel (作者或管理员编辑) -->
      <section v-if="isEditing" class="glass-box edit-panel-card">
        <div class="composer-header">
          <div class="composer-user-meta">
            <span class="composer-avatar composer-avatar-img"><PersonaAvatar :id="currentUserAvatarId" :name="currentUserNick || '创'" :size="38" /></span>
            <div>
              <h3 class="composer-title">编辑讨论帖</h3>
              <p class="composer-sub">修订标题与正文，保存后立即生效并进入合规复审</p>
            </div>
          </div>
          <button type="button" class="btn-close-composer" @click="cancelEdit">×</button>
        </div>

        <div class="composer-body edit-panel-body">
          <input
            v-model="editTitle"
            type="text"
            class="glass-input edit-title-input"
            placeholder="讨论帖标题（至少 5 个字）"
          />
          <textarea
            v-model="editContent"
            class="glass-input edit-content-textarea"
            rows="10"
            placeholder="正文内容（支持 Markdown 排版，至少 10 个字）"
          ></textarea>
        </div>

        <div class="composer-footer">
          <div class="composer-stats">
            <span>字数：{{ editContent.length }}</span>
          </div>
          <div class="composer-actions">
            <button type="button" class="btn-action-ghost" :disabled="isSavingEdit" @click="cancelEdit">
              取消
            </button>
            <button
              type="button"
              class="btn-liquid btn-save-edit"
              :disabled="editTitle.trim().length < 5 || editContent.trim().length < 10 || isSavingEdit"
              @click="saveEdit"
            >
              {{ isSavingEdit ? '正在保存...' : '保存修改' }}
            </button>
          </div>
        </div>
      </section>

      <!-- Zhihu-style Answer Composer Panel (当点击撰写观点时展开) -->
      <section v-if="isWritingAnswer" class="glass-box answer-composer-card">
        <div class="composer-header">
          <div class="composer-user-meta">
            <span class="composer-avatar composer-avatar-img"><PersonaAvatar :id="currentUserAvatarId" :name="currentUserNick || '创'" :size="38" /></span>
            <div>
              <h3 class="composer-title">撰写关于该议题的实战见解与回答</h3>
              <p class="composer-sub">您的观点将以独立回答的形式展示在知乎式观点流中，并支持被提问者采纳</p>
            </div>
          </div>
          <button type="button" class="btn-close-composer" @click="isWritingAnswer = false">×</button>
        </div>

        <div class="composer-body">
          <textarea
            v-model="answerDraft"
            class="glass-input composer-textarea"
            rows="6"
            placeholder="围绕该议题阐述您的实操经验、技术方案或踩坑复盘...（支持 Markdown 排版、代码块与要点列表）"
          ></textarea>
        </div>

        <div class="composer-footer">
          <div class="composer-stats">
            <span>字数：{{ answerDraft.length }}</span>
            <span class="dot-sep">·</span>
            <span>预估阅读：{{ Math.max(1, Math.ceil(answerDraft.length / 300)) }} 分钟</span>
          </div>
          <div class="composer-actions">
            <button
              type="button"
              class="btn-action-ghost"
              :disabled="isSubmittingAnswer"
              @click="isWritingAnswer = false"
            >
              取消
            </button>
            <button
              type="button"
              class="btn-liquid btn-submit-answer"
              :disabled="!answerDraft.trim() || answerDraft.trim().length < 5 || isSubmittingAnswer"
              @click="submitAnswer"
            >
              <svg v-if="!isSubmittingAnswer" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
              <span>{{ isSubmittingAnswer ? '正在编排流水线发布...' : '发布观点回答' }}</span>
            </button>
          </div>
        </div>
      </section>

      <!-- Zhihu-style Answers Section (独立创客深度观点与回答流) -->
      <section class="glass-box answers-stream-section">
        <div class="answers-stream-header">
          <div class="answers-title-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z"/>
              <line x1="9" y1="21" x2="15" y2="21"/>
            </svg>
            <h2 class="answers-title">全部深度观点与回答</h2>
            <span class="answers-badge">{{ answersList.length }} 个实战见解</span>
          </div>

          <div class="answers-sort-group">
            <button
              type="button"
              class="sort-tab-btn"
              :class="{ active: answersSort === 'upvotes' }"
              @click="answersSort = 'upvotes'"
            >
              高赞优先
            </button>
            <button
              type="button"
              class="sort-tab-btn"
              :class="{ active: answersSort === 'latest' }"
              @click="answersSort = 'latest'"
            >
              最新发布
            </button>
          </div>
        </div>

        <!-- Empty Answers Prompt -->
        <div v-if="answersList.length === 0" class="answers-empty-box">
          <div class="empty-icon-ring">💡</div>
          <h4>暂无创客发布深度观点</h4>
          <p>成为第一个针对该议题发表实战经验与避坑复盘的创客！</p>
          <button type="button" class="btn-liquid" @click="isWritingAnswer = true">
            <span>立即撰写第一个回答</span>
          </button>
        </div>

        <!-- Answers List Cards -->
        <div v-else class="answers-card-list">
          <article
            v-for="ans in sortedAnswersList"
            :key="ans.id"
            class="answer-item-card"
            :class="{ 'is-accepted-answer': ans.is_accepted }"
          >
            <!-- Answer Author Meta -->
            <div class="answer-item-header">
              <div class="ans-author-left">
                <div class="ans-author-avatar">
                  {{ (ans.author_name || '客')[0] }}
                </div>
                <div class="ans-author-meta">
                  <div class="ans-author-line">
                    <span class="ans-name">{{ ans.author_name || '实战创客' }}</span>
                    <span v-if="ans.author_title" class="ans-title">{{ ans.author_title }}</span>
                    <span v-if="ans.is_accepted" class="ans-accepted-pill">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                      <span>提问者已采纳最佳观点</span>
                    </span>
                  </div>
                  <div class="ans-sub-line">
                    <span>发表于 {{ formatTime(ans.created_at) }}</span>
                    <span class="dot-sep">·</span>
                    <span v-if="ans.word_count">约 {{ ans.word_count }} 字</span>
                  </div>
                </div>
              </div>

              <!-- Accept / Delete (If Question Author or Admin) -->
              <div class="ans-author-right">
                <button
                  v-if="canAccept"
                  type="button"
                  class="btn-accept-toggle"
                  :class="{ accepted: ans.is_accepted }"
                  @click="handleAcceptAnswer(ans)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span>{{ ans.is_accepted ? '取消采纳' : '采纳此回答' }}</span>
                </button>
                <button
                  v-if="canManageAnswer(ans)"
                  type="button"
                  class="btn-dock-action btn-danger-action"
                  @click="deleteAnswer(ans)"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                  <span>{{ armedDeleteKey === `answer:${ans.id}` ? '确认删除？' : '删除回答' }}</span>
                </button>
              </div>
            </div>

            <!-- Answer Markdown Body -->
            <div
              class="answer-body-content markdown-rendered-content"
              v-html="renderMarkdown(ans.content)"
            ></div>

            <!-- Zhihu Signature Dock for each Answer -->
            <div class="answer-dock-bar">
              <!-- Dual-pill vote group (论坛域 forum.vote ANSWER) -->
              <div class="zhihu-vote-group">
                <button
                  type="button"
                  class="btn-zhihu-vote btn-zhihu-upvote"
                  :class="{ active: ans.user_vote === 'UPVOTE' }"
                  @click="handleAnswerVote(ans, 'UPVOTE')"
                  title="赞同此见解"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 4L3 18h18L12 4z"/>
                  </svg>
                  <span>赞同 {{ ans.upvote_count || 0 }}</span>
                </button>
                <button
                  type="button"
                  class="btn-zhihu-vote btn-zhihu-downvote"
                  :class="{ active: ans.user_vote === 'DOWNVOTE' }"
                  @click="handleAnswerVote(ans, 'DOWNVOTE')"
                  title="反对"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 20l9-14H3l9 14z"/>
                  </svg>
                </button>
              </div>

              <!-- Answer Comments Toggle -->
              <button
                type="button"
                class="btn-dock-action"
                :class="{ active: activeAnswerCommentId === ans.id }"
                @click="toggleAnswerComments(ans.id)"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span>{{ ans.comment_count || 0 }} 条探讨</span>
              </button>
            </div>

            <!-- Expandable Nested Discussion under this specific answer -->
            <div v-if="activeAnswerCommentId === ans.id" class="answer-sub-comments-box">
              <div class="sub-comment-input-row">
                <input
                  v-model="subCommentDraft[ans.id]"
                  type="text"
                  class="glass-input sub-input"
                  placeholder="针对该观点写下您的探讨与交流..."
                  @keydown.enter="submitSubComment(ans)"
                />
                <button
                  type="button"
                  class="btn-liquid btn-sub-submit"
                  :disabled="!subCommentDraft[ans.id] || !subCommentDraft[ans.id].trim()"
                  @click="submitSubComment(ans)"
                >
                  发送
                </button>
              </div>

              <!-- List of comments for this answer -->
              <div v-if="getAnswerComments(ans.id).length > 0" class="sub-comments-list">
                <div
                  v-for="c in getAnswerComments(ans.id)"
                  :key="c.id"
                  class="sub-comment-row"
                >
                  <div class="sub-c-header">
                    <span class="sub-c-name">{{ c.author_name || '独立创客' }}</span>
                    <span class="sub-c-time">{{ formatTime(c.created_at) }}</span>
                  </div>
                  <div class="sub-c-text">{{ c.content }}</div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- Discussions & Comments Section -->
      <section ref="discussionsSectionRef" class="glass-box discussions-section-card">
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
                  :class="{ active: item.user_vote === 'UPVOTE' }"
                  @click="toggleCommentUpvote(item)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"></path>
                  </svg>
                  <span>赞同 {{ item.upvote_count || 0 }}</span>
                </button>

                <button type="button" class="btn-c-action" @click="setReplyTarget(item)">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                  <span>回复</span>
                </button>

                <button
                  v-if="canManageComment(item)"
                  type="button"
                  class="btn-c-action btn-danger-action"
                  @click="deleteComment(item)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                  <span>{{ armedDeleteKey === `comment:${item.id}` ? '确认删除？' : '删除' }}</span>
                </button>
              </div>
            </div>

            <!-- Nested Children -->
            <div v-if="item.children && item.children.length > 0" class="sub-replies-container">
              <div v-for="child in item.children" :key="child.id" class="sub-reply-card">
                <div class="comment-head">
                  <div class="c-author-info">
                    <span class="c-avatar sub-avatar">{{ (child.author_name || '客')[0] }}</span>
                    <span class="c-name">{{ child.author_name || '独立创客' }}</span>
                    <span v-if="child.reply_to_name" class="reply-target-text">
                      回复 <span class="reply-target-tag">@{{ child.reply_to_name }}</span>
                    </span>
                  </div>
                  <span class="c-time">{{ child.created_at || '刚刚' }}</span>
                </div>
                <div class="comment-body-text">{{ child.content }}</div>
                <div class="comment-actions-bar">
                  <button
                    type="button"
                    class="btn-c-action"
                    :class="{ active: child.user_vote === 'UPVOTE' }"
                    @click="toggleCommentUpvote(child)"
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2.8L19.2 11.2C19.8 11.9 19.3 13 18.3 13H15.2V16.2C15.2 16.7 14.8 17.2 14.2 17.2H9.8C9.2 17.2 8.8 16.7 8.8 16.2V13H5.7C4.7 13 4.2 11.9 4.8 11.2L12 2.8Z"></path>
                    </svg>
                    <span>赞同 {{ child.upvote_count || 0 }}</span>
                  </button>
                  <button type="button" class="btn-c-action" @click="setReplyTarget(item, child.author_name)">
                    <span>回复</span>
                  </button>
                  <button
                    v-if="canManageComment(child)"
                    type="button"
                    class="btn-c-action btn-danger-action"
                    @click="deleteComment(child, item)"
                  >
                    <span>{{ armedDeleteKey === `comment:${child.id}` ? '确认删除？' : '删除' }}</span>
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
import OfficialBadge from '@/components/OfficialBadge.vue';
import PersonaAvatar from '@/components/PersonaAvatar.vue';
import ContentDisclaimer from '@/components/ContentDisclaimer.vue';
import ContentInteractionBar from '@/components/ContentInteractionBar.vue';
import { renderMarkdown } from '@/utils/markdown';
import { applyBarChange, applyForumInteractionAliases } from '@/utils/contentInteractions';

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

const emit = defineEmits(['back', 'toast', 'vote', 'update-post', 'delete', 'interaction', 'require-login']);

const currentUserId = computed(() => {
  return props.userSession?.uid || props.userSession?.id || props.userSession?.user?.id || props.userSession?.user?.uid || '';
});

const currentUserAvatarId = computed(() => props.userSession?.profile?.avatar_id || '');
const currentUserNick = computed(() => {
  return props.userSession?.nickname || props.userSession?.username || props.userSession?.user?.nickname || '我';
});

const currentUserRole = computed(() => {
  return (props.userSession?.role || props.userSession?.user?.role || localStorage.getItem('opchub_current_role') || 'MAKER').toUpperCase();
});

function ownsResource(authorId) {
  if (currentUserRole.value === 'ADMIN') return true;
  return Boolean(currentUserId.value && authorId && String(authorId) === String(currentUserId.value));
}

const canDelete = computed(() => ownsResource(props.post?.author_id));
const canEdit = canDelete;
const canAccept = canDelete;

// Thread vote state (知乎式互斥投票，来源：forum.vote / 服务端 user_vote)
const threadUserVote = ref(null);
const threadUpvoteCount = ref(0);
const isFollowing = ref(false);
const isCopied = ref(false);
let copyTimer = null;

// Answers state
const answersList = ref([]);
const answersSort = ref('upvotes');
const isWritingAnswer = ref(false);
const answerDraft = ref('');
const isSubmittingAnswer = ref(false);
const activeAnswerCommentId = ref(null);
const subCommentDraft = ref({});

// Thread edit state
const isEditing = ref(false);
const editTitle = ref('');
const editContent = ref('');
const isSavingEdit = ref(false);

// Arm-then-confirm pattern for destructive answer/comment deletion
const armedDeleteKey = ref('');
let disarmTimer = null;

const replyText = ref('');
const replyTarget = ref(null);
const isSubmitting = ref(false);
const commentTree = ref([]);
const discussionsSectionRef = ref(null);

const sortedAnswersList = computed(() => {
  const list = [...answersList.value];
  if (answersSort.value === 'latest') {
    list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  } else {
    list.sort((a, b) => {
      if (a.is_accepted !== b.is_accepted) return b.is_accepted ? 1 : -1;
      return (b.upvote_count || 0) - (a.upvote_count || 0);
    });
  }
  return list;
});

function canManageAnswer(answer) {
  return ownsResource(answer?.author_id);
}

function canManageComment(comment) {
  return ownsResource(comment?.author_id);
}

watch(
  () => props.post,
  (newPost) => {
    if (newPost) {
      threadUserVote.value = newPost.user_vote || null;
      threadUpvoteCount.value = Number(newPost.upvote_count ?? newPost.upvotes ?? 0);
      isFollowing.value = Boolean(newPost.is_following);
      isEditing.value = false;
      replyTarget.value = null;
      replyText.value = '';
      loadThreadDetail(newPost);
    }
  },
  { immediate: true }
);

function formatTime(isoStr) {
  if (!isoStr) return '刚刚';
  try {
    const diff = Date.now() - new Date(isoStr).getTime();
    if (isNaN(diff)) return '刚刚';
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return `${mins} 分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} 小时前`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} 天前`;
    return new Date(isoStr).toLocaleDateString('zh-CN');
  } catch (e) {
    return '刚刚';
  }
}

function loadThreadDetail(post) {
  if (!post || !post.id) return;
  const tid = String(post.id);

  dispatchGateway('forum.threads.get', { thread_id: tid }, { silent: true }).then((res) => {
    if (res.ok && res.data) {
      if (Array.isArray(res.data.answers)) {
        answersList.value = res.data.answers;
      }
      if (Array.isArray(res.data.comments)) {
        commentTree.value = res.data.comments.map((node) => mapCommentNode(node));
      }
      if (res.data.thread) {
        const t = res.data.thread;
        isFollowing.value = Boolean(t.is_following);
        threadUserVote.value = t.user_vote || null;
        threadUpvoteCount.value = Number(t.upvote_count || 0);
        props.post.user_vote = t.user_vote || null;
        props.post.upvote_count = Number(t.upvote_count || 0);
        props.post.upvotes = Number(t.upvote_count || 0);
        props.post.is_upvoted = (t.user_vote === 'UPVOTE');
        props.post.answer_count = Number(t.answer_count || 0);
        props.post.comment_count = Number(t.comment_count || 0);
        props.post.replies = Number(t.comment_count || 0);
      }
    }
  }).catch(() => {});
}

function mapCommentNode(node) {
  return {
    id: node.id,
    target_type: node.target_type,
    target_id: node.target_id,
    author_id: node.author_id || '',
    author_name: node.author_name || (node.author_id ? `创客_${node.author_id.slice(0, 6)}` : '实战创客'),
    created_at: node.created_at,
    is_accepted: Boolean(node.is_accepted),
    upvote_count: node.upvote_count || 0,
    user_vote: node.user_vote || null,
    content: node.content,
    children: (node.children || []).map((sub) => ({
      id: sub.id,
      target_type: sub.target_type,
      target_id: sub.target_id,
      author_id: sub.author_id || '',
      author_name: sub.author_name || (sub.author_id ? `创客_${sub.author_id.slice(0, 6)}` : '出海创客'),
      created_at: sub.created_at,
      upvote_count: sub.upvote_count || 0,
      user_vote: sub.user_vote || null,
      content: sub.content,
      reply_to_name: null,
    })),
  };
}

async function handleThreadVote(vtype) {
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以进行观点赞同或投票互动', type: 'INFO' });
    return;
  }

  const prevVote = threadUserVote.value;
  const prevCount = threadUpvoteCount.value;

  if (vtype === 'UPVOTE') {
    if (threadUserVote.value === 'UPVOTE') {
      threadUserVote.value = null;
      threadUpvoteCount.value = Math.max(0, threadUpvoteCount.value - 1);
    } else {
      threadUserVote.value = 'UPVOTE';
      threadUpvoteCount.value += 1;
    }
  } else if (vtype === 'DOWNVOTE') {
    if (threadUserVote.value === 'DOWNVOTE') {
      threadUserVote.value = null;
    } else {
      if (threadUserVote.value === 'UPVOTE') {
        threadUpvoteCount.value = Math.max(0, threadUpvoteCount.value - 1);
      }
      threadUserVote.value = 'DOWNVOTE';
    }
  }

  try {
    const res = await dispatchGateway('forum.vote', {
      user_id: currentUserId.value,
      target_type: 'THREAD',
      target_id: String(props.post.id),
      vote_type: vtype,
    }, { silent: true });

    if (res.ok && res.data) {
      threadUserVote.value = res.data.user_vote;
      threadUpvoteCount.value = res.data.upvote_count;
      props.post.user_vote = res.data.user_vote;
      props.post.upvote_count = res.data.upvote_count;
      props.post.upvotes = res.data.upvote_count;
      props.post.is_upvoted = (res.data.user_vote === 'UPVOTE');
      emit('vote', {
        post: props.post,
        userVote: res.data.user_vote,
        upvoteCount: res.data.upvote_count,
        downvoteCount: res.data.downvote_count,
      });
    } else {
      threadUserVote.value = prevVote;
      threadUpvoteCount.value = prevCount;
      emit('toast', { title: '投票失败', message: res.error || '无法记录投票，请重试', type: 'ERROR' });
    }
  } catch (e) {
    threadUserVote.value = prevVote;
    threadUpvoteCount.value = prevCount;
    emit('toast', { title: '操作异常', message: '网络或服务异常，请重试', type: 'ERROR' });
  }
}

function onInteractionChanged(payload) {
  applyBarChange(props.post, payload);
  applyForumInteractionAliases(props.post);
  emit('interaction', { post: props.post, ...payload });
}

function scrollToDiscussions() {
  discussionsSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toggleComposer() {
  isEditing.value = false;
  isWritingAnswer.value = !isWritingAnswer.value;
}

function openEditPanel() {
  isWritingAnswer.value = false;
  editTitle.value = props.post?.title || '';
  editContent.value = props.post?.content || '';
  isEditing.value = true;
}

function cancelEdit() {
  isEditing.value = false;
  editTitle.value = '';
  editContent.value = '';
}

async function saveEdit() {
  const title = editTitle.value.trim();
  const content = editContent.value.trim();
  if (title.length < 5 || content.length < 10 || isSavingEdit.value) return;

  isSavingEdit.value = true;
  try {
    const res = await dispatchGateway('forum.threads.update', {
      thread_id: String(props.post.id),
      title,
      content,
    });
    if (res.ok && res.data) {
      props.post.title = res.data.title || title;
      props.post.content = res.data.content || content;
      props.post.updated_at = res.data.updated_at || props.post.updated_at;
      emit('update-post', props.post);
      isEditing.value = false;
      emit('toast', { title: '修改已保存', message: '讨论帖内容已更新并通过合规复审。', type: 'SUCCESS' });
    } else {
      emit('toast', { title: '保存失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '保存异常', message: '编辑服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    isSavingEdit.value = false;
  }
}

async function handleToggleFollow() {
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以关注该议题', type: 'INFO' });
    return;
  }
  try {
    const res = await dispatchGateway('forum.threads.follow', { thread_id: String(props.post.id) });
    if (res.ok && res.data) {
      isFollowing.value = Boolean(res.data.is_following);
      props.post.is_following = isFollowing.value;
      emit('toast', {
        title: isFollowing.value ? '已关注议题' : '已取消关注',
        message: isFollowing.value ? '新创客发表观点回答时将提醒您' : '已取消对该议题的关注',
        type: 'SUCCESS',
      });
    }
  } catch (e) {
    emit('toast', { title: '操作失败', message: '关注服务异常，请重试', type: 'ERROR' });
  }
}

async function submitAnswer() {
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以发布深度见解', type: 'INFO' });
    return;
  }
  const text = answerDraft.value.trim();
  if (text.length < 5) {
    emit('toast', { title: '内容过短', message: '回答内容至少需要 5 个字', type: 'WARNING' });
    return;
  }

  isSubmittingAnswer.value = true;
  try {
    const res = await dispatchGateway('forum.answers.publish', {
      thread_id: String(props.post.id),
      content: text,
    });

    if (res.ok && res.data) {
      answersList.value.unshift(res.data);
      answerDraft.value = '';
      isWritingAnswer.value = false;
      props.post.answer_count = (props.post.answer_count || 0) + 1;
      emit('update-post', props.post);
      emit('toast', {
        title: '观点回答发布成功',
        message: '您的实战见解已通过平台安全审查并发布！',
        type: 'SUCCESS',
      });
    } else {
      emit('toast', { title: '发布失败', message: res.error || '发布异常，请重试', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '系统异常', message: '流水线服务暂不可用，请稍后重试', type: 'ERROR' });
  } finally {
    isSubmittingAnswer.value = false;
  }
}

async function handleAcceptAnswer(answer) {
  try {
    const res = await dispatchGateway('forum.answers.accept', {
      thread_id: String(props.post.id),
      answer_id: String(answer.id),
      operator_user_id: currentUserId.value,
    });
    if (res.ok && res.data) {
      const isAccepted = Boolean(res.data.is_accepted);
      answersList.value.forEach((a) => {
        if (a.id === answer.id) {
          a.is_accepted = isAccepted;
        } else if (isAccepted) {
          a.is_accepted = false;
        }
      });
      props.post.accepted_answer_id = isAccepted ? answer.id : null;
      emit('toast', {
        title: isAccepted ? '已采纳最佳观点' : '已取消采纳',
        message: isAccepted ? '该观点已被标记为题主推荐实战方案' : '已更新采纳状态',
        type: 'SUCCESS',
      });
    } else {
      emit('toast', { title: '操作失败', message: res.error || '无法采纳该见解', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '操作异常', message: '服务异常，请稍后重试', type: 'ERROR' });
  }
}

async function handleAnswerVote(answer, voteType) {
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以进行赞同或反对', type: 'INFO' });
    return;
  }

  const prevVote = answer.user_vote;
  const prevUp = answer.upvote_count || 0;
  const prevDown = answer.downvote_count || 0;

  if (voteType === 'UPVOTE') {
    if (answer.user_vote === 'UPVOTE') {
      answer.user_vote = null;
      answer.upvote_count = Math.max(0, prevUp - 1);
    } else {
      if (answer.user_vote === 'DOWNVOTE') {
        answer.downvote_count = Math.max(0, prevDown - 1);
      }
      answer.user_vote = 'UPVOTE';
      answer.upvote_count = prevUp + 1;
    }
  } else if (voteType === 'DOWNVOTE') {
    if (answer.user_vote === 'DOWNVOTE') {
      answer.user_vote = null;
      answer.downvote_count = Math.max(0, prevDown - 1);
    } else {
      if (answer.user_vote === 'UPVOTE') {
        answer.upvote_count = Math.max(0, prevUp - 1);
      }
      answer.user_vote = 'DOWNVOTE';
      answer.downvote_count = prevDown + 1;
    }
  }

  try {
    const res = await dispatchGateway('forum.vote', {
      user_id: currentUserId.value,
      target_type: 'ANSWER',
      target_id: String(answer.id),
      vote_type: voteType,
    }, { silent: true });

    if (res.ok && res.data) {
      answer.user_vote = res.data.user_vote;
      answer.upvote_count = res.data.upvote_count;
      answer.downvote_count = res.data.downvote_count;
    } else {
      answer.user_vote = prevVote;
      answer.upvote_count = prevUp;
      answer.downvote_count = prevDown;
    }
  } catch (e) {
    answer.user_vote = prevVote;
    answer.upvote_count = prevUp;
    answer.downvote_count = prevDown;
  }
}

function toggleAnswerComments(ansId) {
  if (activeAnswerCommentId.value === ansId) {
    activeAnswerCommentId.value = null;
  } else {
    activeAnswerCommentId.value = ansId;
  }
}

function getAnswerComments(ansId) {
  return commentTree.value.filter((c) => String(c.target_id) === String(ansId));
}

async function submitSubComment(answer) {
  const draft = subCommentDraft.value[answer.id];
  if (!draft || !draft.trim()) return;
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以发表交流探讨', type: 'INFO' });
    return;
  }

  try {
    const res = await dispatchGateway('forum.comments.create', {
      thread_id: String(props.post.id),
      target_type: 'ANSWER',
      target_id: String(answer.id),
      content: draft.trim(),
      author_id: currentUserId.value,
      author_name: currentUserNick.value,
    });
    if (res.ok && res.data) {
      commentTree.value.push(mapCommentNode(res.data));
      answer.comment_count = (answer.comment_count || 0) + 1;
      props.post.comment_count = (props.post.comment_count || 0) + 1;
      props.post.replies = props.post.comment_count;
      subCommentDraft.value[answer.id] = '';
      emit('toast', { title: '探讨已发表', message: '您的观点补充已成功发表！', type: 'SUCCESS' });
    } else {
      emit('toast', { title: '发表失败', message: res.error || '请稍后重试', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '发表失败', message: '网络服务异常', type: 'ERROR' });
  }
}

async function toggleCommentUpvote(item) {
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以参与探讨互动', type: 'INFO' });
    return;
  }

  const prevVote = item.user_vote || null;
  const prevCount = item.upvote_count || 0;
  const vtype = prevVote === 'UPVOTE' ? 'CANCEL' : 'UPVOTE';

  item.user_vote = vtype === 'UPVOTE' ? 'UPVOTE' : null;
  item.upvote_count = Math.max(0, prevCount + (vtype === 'UPVOTE' ? 1 : -1));

  try {
    const res = await dispatchGateway('forum.vote', {
      user_id: currentUserId.value,
      target_type: 'COMMENT',
      target_id: String(item.id),
      vote_type: vtype,
    }, { silent: true });
    if (res.ok && res.data) {
      item.user_vote = res.data.user_vote;
      item.upvote_count = res.data.upvote_count;
    } else {
      item.user_vote = prevVote;
      item.upvote_count = prevCount;
    }
  } catch (e) {
    item.user_vote = prevVote;
    item.upvote_count = prevCount;
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
  if (!currentUserId.value) {
    emit('require-login');
    emit('toast', { title: '需要登录', message: '请先登录以发表实战见解', type: 'INFO' });
    return;
  }

  isSubmitting.value = true;
  try {
    const parentId = replyTarget.value?.parentId || null;
    const parent = parentId ? commentTree.value.find((c) => c.id === parentId) : null;

    const res = await dispatchGateway('forum.comments.create', {
      thread_id: String(props.post.id),
      target_type: parent ? (parent.target_type || 'THREAD') : 'THREAD',
      target_id: parent ? (parent.target_id || String(props.post.id)) : String(props.post.id),
      content,
      author_id: currentUserId.value,
      author_name: currentUserNick.value,
      parent_id: parentId,
      reply_to_user_id: parent ? (parent.author_id || null) : null,
    });

    if (res.ok && res.data) {
      const node = mapCommentNode(res.data);
      node.reply_to_name = replyTarget.value?.authorName || null;
      if (parent) {
        if (!parent.children) parent.children = [];
        parent.children.push(node);
      } else {
        commentTree.value.unshift(node);
      }
      props.post.comment_count = (props.post.comment_count || 0) + 1;
      props.post.replies = props.post.comment_count;
      replyText.value = '';
      replyTarget.value = null;
      emit('toast', {
        title: '发表成功',
        message: '您的实战见解已通过审查并即时汇入风暴讨论树！',
        type: 'SUCCESS',
      });
    } else {
      emit('toast', { title: '发表失败', message: res.error || '请稍后重试', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '发表失败', message: '网络或服务异常，请稍后重试', type: 'ERROR' });
  } finally {
    isSubmitting.value = false;
  }
}

function requestConfirm(key, action) {
  if (armedDeleteKey.value === key) {
    armedDeleteKey.value = '';
    clearTimeout(disarmTimer);
    action();
    return;
  }
  armedDeleteKey.value = key;
  clearTimeout(disarmTimer);
  disarmTimer = setTimeout(() => {
    armedDeleteKey.value = '';
  }, 3000);
}

function countSubtree(comment) {
  let total = 1;
  for (const child of comment.children || []) {
    total += countSubtree(child);
  }
  return total;
}

function removeFromCommentTree(commentId) {
  const idx = commentTree.value.findIndex((c) => c.id === commentId);
  if (idx !== -1) {
    const [removed] = commentTree.value.splice(idx, 1);
    return countSubtree(removed);
  }
  for (const root of commentTree.value) {
    const children = root.children || [];
    const childIdx = children.findIndex((c) => c.id === commentId);
    if (childIdx !== -1) {
      const [removed] = children.splice(childIdx, 1);
      return countSubtree(removed);
    }
  }
  return 0;
}

function deleteComment(comment, parentComment = null) {
  requestConfirm(`comment:${comment.id}`, async () => {
    if (!currentUserId.value) {
      emit('require-login');
      return;
    }
    const subtreeSize = countSubtree(comment);
    try {
      const res = await dispatchGateway('forum.comments.delete', {
        comment_id: String(comment.id),
      });
      if (res.ok && res.data) {
        removeFromCommentTree(comment.id);
        props.post.comment_count = Math.max(0, (props.post.comment_count || 0) - subtreeSize);
        props.post.replies = props.post.comment_count;
        emit('toast', { title: '评论已删除', message: '该评论及其子评论已同步移除。', type: 'SUCCESS' });
      } else {
        emit('toast', { title: '删除失败', message: res.error || '请稍后重试', type: 'ERROR' });
      }
    } catch (e) {
      emit('toast', { title: '删除异常', message: '服务暂时不可用，请稍后重试', type: 'ERROR' });
    }
  });
}

function deleteAnswer(answer) {
  requestConfirm(`answer:${answer.id}`, async () => {
    if (!currentUserId.value) {
      emit('require-login');
      return;
    }
    try {
      const res = await dispatchGateway('forum.answers.delete', {
        answer_id: String(answer.id),
      });
      if (res.ok && res.data) {
        answersList.value = answersList.value.filter((a) => a.id !== answer.id);
        const removedComments = getAnswerComments(answer.id).length;
        if (removedComments > 0) {
          commentTree.value = commentTree.value.filter((c) => String(c.target_id) !== String(answer.id));
        }
        props.post.answer_count = Math.max(0, (props.post.answer_count || 0) - 1);
        props.post.comment_count = Math.max(0, (props.post.comment_count || 0) - removedComments);
        props.post.replies = props.post.comment_count;
        if (props.post.accepted_answer_id === answer.id) {
          props.post.accepted_answer_id = null;
        }
        emit('toast', { title: '回答已删除', message: '该观点回答及其探讨与投票已同步移除。', type: 'SUCCESS' });
      } else {
        emit('toast', { title: '删除失败', message: res.error || '请稍后重试', type: 'ERROR' });
      }
    } catch (e) {
      emit('toast', { title: '删除异常', message: '服务暂时不可用，请稍后重试', type: 'ERROR' });
    }
  });
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

  const shareText = `【OpcHub 头脑风暴实战经验分享】\n《${props.post?.title || '实战经验'}》\n分类：${categoryLabel.value} · 作者：${props.post?.author || ''}\n查看详情与交流探讨：\n${shareUrl}`;

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

.btn-header-ghost-action {
  display: inline-flex;
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

.btn-header-ghost-action:hover,
.btn-header-ghost-action.active {
  background: var(--glass-surface-hover);
  color: var(--accent);
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

/* Bottom Action Cluster: vote group + write + follow */
.article-bottom-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 4px 0 10px;
}

.vote-group-big .btn-zhihu-vote {
  padding: 9px 18px;
  font-size: 13.5px;
  gap: 6px;
}

.btn-action-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: var(--radius-sm, 6px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s ease;
}

.btn-action-ghost:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--glass-surface-hover);
}

.btn-action-ghost.active {
  background: var(--accent-glass);
  border-color: var(--accent);
  color: var(--accent);
}

.btn-action-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail-interaction-row {
  padding-top: 10px;
  border-top: 1px dashed var(--glass-border-subtle);
}

.btn-danger-action {
  color: var(--text-tertiary);
}

.btn-danger-action:hover {
  color: var(--status-danger) !important;
  background: var(--status-danger-soft) !important;
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

/* Thread Edit Panel */
.edit-panel-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-title-input {
  width: 100%;
  font-size: 15px;
  font-weight: 600;
  padding: 10px 14px;
}

.edit-content-textarea {
  width: 100%;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.65;
  resize: vertical;
  min-height: 180px;
}

.btn-save-edit {
  padding: 9px 20px;
  font-size: 13px;
}

.btn-save-edit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Zhihu Answer Composer & Answer Stream Styles */
.answer-composer-card {
  padding: 24px;
  border-radius: var(--radius-lg, 16px);
  margin-bottom: 24px;
  background: var(--glass-surface);
  border: 1px solid var(--accent);
  box-shadow: 0 4px 20px rgba(0, 113, 227, 0.08);
}

.composer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.composer-user-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.composer-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.composer-avatar-img {
  background: transparent;
  overflow: hidden;
  padding: 0;
}

.composer-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px 0;
}

.composer-sub {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin: 0;
}

.btn-close-composer {
  background: transparent;
  border: none;
  font-size: 20px;
  color: var(--text-tertiary);
  cursor: pointer;
  line-height: 1;
}

.composer-textarea {
  width: 100%;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  min-height: 120px;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
}

.composer-stats {
  font-size: 12px;
  color: var(--text-tertiary);
}

.composer-actions {
  display: flex;
  gap: 10px;
}

.answers-stream-section {
  padding: 28px;
  border-radius: var(--radius-lg, 16px);
  margin-bottom: 24px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
}

.answers-stream-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--glass-border-subtle);
  margin-bottom: 20px;
}

.answers-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.answers-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.answers-badge {
  font-size: 11.5px;
  color: var(--accent);
  background: rgba(0, 113, 227, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.answers-sort-group {
  display: flex;
  gap: 6px;
}

.sort-tab-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.sort-tab-btn.active {
  background: var(--glass-surface-subtle);
  color: var(--accent);
  font-weight: 600;
  border-color: var(--glass-border-subtle);
}

.answers-card-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.answers-empty-box {
  padding: 36px 20px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-icon-ring {
  font-size: 26px;
}

.answer-item-card {
  padding: 22px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  transition: all 0.2s ease;
}

.answer-item-card.is-accepted-answer {
  border-color: rgba(52, 199, 89, 0.45);
  box-shadow: 0 2px 14px rgba(52, 199, 89, 0.08);
}

.answer-item-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.ans-author-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ans-author-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--glass-surface-hover);
  color: var(--accent);
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ans-author-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ans-author-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ans-name {
  font-weight: 700;
  font-size: 13.5px;
  color: var(--text-primary);
}

.ans-title {
  font-size: 12px;
  color: var(--text-secondary);
}

.ans-accepted-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(52, 199, 89, 0.15);
  color: #34c759;
  border: 1px solid rgba(52, 199, 89, 0.3);
}

.ans-sub-line {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.ans-author-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-accept-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--accent);
  color: var(--accent);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-accept-toggle:hover {
  background: rgba(0, 113, 227, 0.1);
}

.btn-accept-toggle.accepted {
  background: rgba(52, 199, 89, 0.12);
  border-color: #34c759;
  color: #34c759;
}

.answer-body-content {
  font-size: 14.5px;
  line-height: 1.7;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.answer-dock-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--glass-border-subtle);
}

.btn-dock-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 5px 8px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-dock-action:hover,
.btn-dock-action.active {
  color: var(--accent);
  background: rgba(0, 113, 227, 0.08);
}

.answer-sub-comments-box {
  margin-top: 14px;
  padding: 14px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.025);
  border: 1px solid var(--glass-border-subtle);
}

.sub-comment-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.sub-input {
  flex: 1;
  font-size: 13px;
  padding: 6px 10px;
}

.btn-sub-submit {
  font-size: 12px;
  padding: 6px 14px;
}

.sub-comments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sub-comment-row {
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.sub-c-header {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  margin-bottom: 4px;
}

.sub-c-name {
  font-weight: 600;
  color: var(--text-primary);
}

.sub-c-time {
  color: var(--text-tertiary);
}

.sub-c-text {
  font-size: 13px;
  color: var(--text-secondary);
}

/* Zhihu Vote Group */
.zhihu-vote-group {
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
  background: rgba(0, 113, 227, 0.08);
  border: 1px solid rgba(0, 113, 227, 0.15);
  overflow: hidden;
}

.btn-zhihu-vote {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 9px;
  border: none;
  background: transparent;
  color: var(--accent, #0071E3);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-zhihu-vote:hover {
  background: rgba(0, 113, 227, 0.16);
}

.btn-zhihu-vote.active {
  background: var(--accent, #0071E3);
  color: #ffffff;
}

.btn-zhihu-downvote {
  padding: 5px 7px;
  border-left: 1px solid rgba(0, 113, 227, 0.15);
}

[data-theme="dark"] .answer-composer-card,
[data-theme="dark"] .answers-stream-section {
  background: rgba(26, 29, 36, 0.72);
}

[data-theme="dark"] .answer-item-card {
  background: rgba(18, 20, 29, 0.65);
}

[data-theme="dark"] .zhihu-vote-group {
  background: rgba(41, 151, 255, 0.1);
  border-color: rgba(41, 151, 255, 0.2);
}

[data-theme="dark"] .btn-zhihu-vote {
  color: var(--accent, #2997FF);
}

[data-theme="dark"] .btn-zhihu-vote.active {
  background: var(--accent, #2997FF);
  color: #ffffff;
}
</style>
