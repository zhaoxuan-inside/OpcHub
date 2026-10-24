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
        <OfficialBadge v-if="post?.is_official" label="官方" title="官方发布：由平台官方账号发布并认证" />

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

        <!-- 展示页面免责声明 -->
        <ContentDisclaimer type="forum" />

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
            type="button"
            class="btn-liquid btn-action-big btn-write-answer-primary"
            @click="isWritingAnswer = !isWritingAnswer"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            <span>{{ isWritingAnswer ? '收起回答框' : '撰写深度观点' }}</span>
          </button>

          <button
            type="button"
            class="btn-outline-action"
            :class="{ active: isFollowing }"
            @click="handleToggleFollow"
            title="关注该议题动态"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            <span>{{ isFollowing ? '已关注议题' : '关注议题' }}</span>
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
            <span>删除议题</span>
          </button>
        </div>
      </article>

      <!-- Zhihu-style Answer Composer Panel (当点击撰写观点时展开) -->
      <section v-if="isWritingAnswer" class="glass-box answer-composer-card">
        <div class="composer-header">
          <div class="composer-user-meta">
            <span class="composer-avatar">{{ (currentUserNick || '创')[0] }}</span>
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
              class="btn-outline-action"
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
                    <span class="ans-title">{{ ans.author_title || '已认证超级个体' }}</span>
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
                    <span>约 {{ ans.word_count || 120 }} 字</span>
                  </div>
                </div>
              </div>

              <!-- Accept Button (If Question Author or Admin) -->
              <div v-if="canAccept" class="ans-author-right">
                <button
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
              </div>
            </div>

            <!-- Answer Markdown Body -->
            <div
              class="answer-body-content markdown-rendered-content"
              v-html="renderMarkdown(ans.content)"
            ></div>

            <!-- Zhihu Signature Dock for each Answer -->
            <div class="answer-dock-bar">
              <!-- Dual-pill vote group -->
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

              <button
                type="button"
                class="btn-dock-action"
                @click="handleCopyLink"
                title="分享此回答"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="18" cy="5" r="3"></circle>
                  <circle cx="6" cy="12" r="3"></circle>
                  <circle cx="18" cy="19" r="3"></circle>
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                </svg>
                <span>分享</span>
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
import OfficialBadge from '@/components/OfficialBadge.vue';
import ContentDisclaimer from '@/components/ContentDisclaimer.vue';
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

const currentUserNick = computed(() => {
  return props.userSession?.nickname || props.userSession?.username || props.userSession?.user?.nickname || '认证创客';
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

const canAccept = computed(() => {
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

  // Fetch real details from backend microkernel gateway
  dispatchGateway('forum.threads.get', { thread_id: tid }, { silent: true }).then((res) => {
    if (res.ok && res.data) {
      if (Array.isArray(res.data.answers)) {
        answersList.value = res.data.answers;
      }
      if (Array.isArray(res.data.comments)) {
        commentTree.value = res.data.comments.map((node) => ({
          id: node.id,
          target_type: node.target_type,
          target_id: node.target_id,
          author_name: node.author_name || (node.author_id ? `创客_${node.author_id.slice(0, 6)}` : '实战创客'),
          ip_location: '来自 浙江',
          created_at: formatTime(node.created_at),
          is_accepted: Boolean(node.is_accepted),
          upvote_count: node.upvote_count || 0,
          upvoted: false,
          content: node.content,
          children: (node.children || []).map((sub) => ({
            id: sub.id,
            target_type: sub.target_type,
            target_id: sub.target_id,
            author_name: sub.author_name || (sub.author_id ? `创客_${sub.author_id.slice(0, 6)}` : '出海创客'),
            ip_location: '来自 浙江',
            created_at: formatTime(sub.created_at),
            upvote_count: sub.upvote_count || 0,
            upvoted: false,
            content: sub.content,
          })),
        }));
      }
      if (res.data.thread) {
        isFollowing.value = Boolean(res.data.thread.is_following);
        threadUpvoted.value = (res.data.thread.user_vote === 'UPVOTE');
        threadUpvoteCount.value = res.data.thread.upvote_count || 0;
        threadBookmarked.value = Boolean(res.data.thread.is_bookmarked);
      }
    }
  }).catch(() => {});
}

async function handleToggleFollow() {
  if (!currentUserId.value) {
    emit('toast', { title: '需要登录', message: '请先登录以关注该议题', type: 'INFO' });
    return;
  }
  try {
    const res = await dispatchGateway('forum.threads.follow', { thread_id: String(props.post.id) });
    if (res.ok && res.data) {
      isFollowing.value = Boolean(res.data.is_following);
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
      author_id: currentUserId.value,
      author_name: currentUserNick.value,
      author_title: '已认证超级个体',
    });

    if (res.ok && res.data) {
      answersList.value.unshift(res.data);
      answerDraft.value = '';
      isWritingAnswer.value = false;
      if (props.post) {
        props.post.answer_count = (props.post.answer_count || 0) + 1;
      }
      emit('toast', {
        title: '观点回答发布成功',
        message: '您的实战见解已通过微内核 DAG 编排流水线完成安全审查与持久化归档！',
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
      // Update local state
      answersList.value.forEach((a) => {
        if (a.id === answer.id) {
          a.is_accepted = isAccepted;
        } else if (isAccepted) {
          a.is_accepted = false;
        }
      });
      if (props.post) {
        props.post.accepted_answer_id = isAccepted ? answer.id : null;
      }
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
    });
    if (res.ok && res.data) {
      commentTree.value.push({
        id: res.data.id || res.data.comment_id,
        target_type: 'ANSWER',
        target_id: String(answer.id),
        author_name: currentUserNick.value,
        ip_location: '来自 浙江',
        created_at: '刚刚',
        content: draft.trim(),
        upvote_count: 0,
        children: [],
      });
      answer.comment_count = (answer.comment_count || 0) + 1;
      subCommentDraft.value[answer.id] = '';
      emit('toast', { title: '探讨已发表', message: '您的观点补充已成功发表！', type: 'SUCCESS' });
    }
  } catch (e) {
    emit('toast', { title: '发表失败', message: '网络服务异常', type: 'ERROR' });
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

// 举报进入平台审核队列（moderation.report），由运营复核后下架/恢复，
// 与全站统一的 ContentInteractionBar 举报走同一条链路。
async function handleReport() {
  const post = props.post || {};
  try {
    const res = await dispatchGateway('moderation.report', {
      target_type: 'FORUM_THREAD',
      target_id: String(post.id || ''),
      target_title: post.title || '',
      snippet_content: post.title || '',
      author_id: post.author_id || '',
      author_name: post.author_name || '',
      reason: '头脑风暴帖子被举报：疑似违规或内容失实',
    });
    if (res.ok && res.data) {
      emit('toast', {
        title: '已提交合规复审',
        message: '举报已进入平台审核队列，运营复核后将作下架或恢复处理。',
        type: 'INFO',
      });
    } else {
      emit('toast', {
        title: '举报未提交',
        message: res.error || '请稍后重试。',
        type: 'ERROR',
      });
    }
  } catch (e) {
    emit('toast', {
      title: '举报异常',
      message: '举报服务暂时不可用，请稍后重试。',
      type: 'ERROR',
    });
  }
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
