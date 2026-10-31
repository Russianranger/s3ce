.method stop()V
    # S3CE: one track generation and serialized lifecycle ownership.
    .locals 3

    monitor-enter p0
    :s3ce_try_start
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-eqz v0, :s3ce_done
    # Retire before calling platform APIs; queued delegates keep the old track.
    const/4 v1, 0x0
    iput-object v1, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    const-string v1, "SoundPlayer"
    const-string v2, "stopping sound"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    const/4 v1, 0x0
    invoke-virtual {v0, v1}, Landroid/media/AudioTrack;->setPlaybackPositionUpdateListener(Landroid/media/AudioTrack$OnPlaybackPositionUpdateListener;)V
    invoke-virtual {v0, v1}, Landroid/media/AudioTrack;->setPositionNotificationPeriod(I)I
    invoke-virtual {v0}, Landroid/media/AudioTrack;->stop()V
    invoke-virtual {v0}, Landroid/media/AudioTrack;->flush()V
    invoke-virtual {v0}, Landroid/media/AudioTrack;->release()V
    const-string v1, "SoundPlayer"
    const-string v2, "done stopping sound"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :s3ce_done
    :s3ce_try_end
    monitor-exit p0
    return-void
    .catchall {:s3ce_try_start .. :s3ce_try_end} :s3ce_catchall
    :s3ce_catchall
    move-exception v2
    monitor-exit p0
    throw v2
.end method
